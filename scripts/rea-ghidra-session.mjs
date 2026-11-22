import { promises as fs } from "node:fs";
import { Client } from "@modelcontextprotocol/client";
import { StdioClientTransport } from "@modelcontextprotocol/client/stdio";

const binaryPath = process.argv[2];
if (!binaryPath || !binaryPath.startsWith("/")) throw new Error("An absolute Mach-O path is required.");
await fs.mkdir("reports", { recursive: true });
const client = new Client({ name: "ultron-ghidra-worker", version: "1.0.0" });
const transport = new StdioClientTransport({
  command: "rea",
  args: ["mcp"],
  stderr: "pipe"
});
transport.stderr?.on("data", chunk => { fs.appendFile("reports/rea-mcp-stderr.log", chunk).catch(() => {}); });
const outputs = new Map();
let opened = false;
let toolMap = new Map();

function parseToolResult(result) {
  if (result?.structuredContent !== undefined) return result.structuredContent;
  const blocks = (result?.content || []).filter(item => item.type === "text").map(item => item.text);
  if (blocks.length === 1) {
    try { return JSON.parse(blocks[0]); } catch {}
  }
  return { content: blocks };
}
function walk(value, visit) {
  if (!value) return;
  if (Array.isArray(value)) return value.forEach(item => walk(item, visit));
  if (typeof value !== "object") return;
  visit(value);
  for (const child of Object.values(value)) walk(child, visit);
}
function procedureCandidates(value) {
  const found = new Map();
  walk(value, item => {
    const procedure = item.procedure && typeof item.procedure === "object" ? item.procedure : item;
    const address = item.address || procedure.address || item.entry || item.entry_address || item.start_address;
    const name = procedure.name || item.name || procedure.symbol || item.symbol || procedure.label || item.label;
    const external = procedure.external === true || item.external === true;
    if (external) return;
    if (typeof address === "string" || typeof name === "string") {
      const identity = typeof name === "string" && name.length ? name : address;
      if (typeof identity === "string" && identity.length) found.set(identity, {
        procedure: identity,
        address: typeof address === "string" ? address : null,
        name: typeof name === "string" ? name : identity
      });
    }
  });
  return [...found.values()];
}
function argumentsFor(tool, seed = {}) {
  const schema = tool?.inputSchema || {};
  const properties = schema.properties || {};
  const required = schema.required || [];
  const args = { ...seed };
  if (properties.detail && !args.detail) {
    const choices = properties.detail.enum || properties.detail.anyOf?.flatMap(x => x.enum || []) || [];
    if (choices.includes("complete")) args.detail = "complete";
    else if (choices.includes("summary")) args.detail = "summary";
  }
  if (properties.limit && args.limit === undefined) args.limit = 100;
  if (properties.offset && args.offset === undefined) args.offset = 0;
  for (const key of required) {
    if (args[key] !== undefined) continue;
    const property = properties[key] || {};
    const type = property.type || (property.anyOf || []).find(x => x.type)?.type;
    if (type === "string") args[key] = key === "procedure" ? "main" : "";
    else if (type === "integer" || type === "number") args[key] = 100;
    else if (type === "boolean") args[key] = false;
    else if (type === "array") args[key] = [];
    else if (type === "object") args[key] = {};
  }
  return args;
}
async function call(name, args = {}, timeout = 1200000, reportName = name) {
  const result = await client.callTool({ name, arguments: args }, {
    timeout
  });
  const parsed = parseToolResult(result);
  outputs.set(reportName, parsed);
  await fs.writeFile(`reports/ghidra-${reportName}.json`, JSON.stringify(parsed, null, 2), { mode: 0o600 });
  if (result.isError) throw new Error(`REA tool ${name} returned an error; inspect the protected worker report.`);
  return parsed;
}

try {
  await client.connect(transport);
  const catalog = await client.listTools();
  toolMap = new Map((catalog.tools || []).map(tool => [tool.name, tool]));
  for (const required of ["binary_session", "open_binary", "binary_overview", "list_procedures", "analyze_function", "close_binary"]) {
    if (!toolMap.has(required)) throw new Error(`Pinned REA package does not advertise required tool ${required}.`);
  }

  await call("binary_session", {}, 120000, "binary-session-before-open");
  const openArgs = argumentsFor(toolMap.get("open_binary"), { path: binaryPath, provider_id: "ghidra" });
  await call("open_binary", openArgs, 120000);
  opened = true;

  const sessionInfo = await call("binary_session", {}, 120000, "binary-session-after-open");
  function findKey(value, key) {
    if (!value || typeof value !== "object") return undefined;
    if (Object.prototype.hasOwnProperty.call(value, key)) return value[key];
    for (const child of Object.values(value)) {
      const found = findKey(child, key);
      if (found !== undefined) return found;
    }
    return undefined;
  }
  const rawAvailability = findKey(sessionInfo, "tool_availability");
  const toolAvailability = Array.isArray(rawAvailability) ? rawAvailability :
    rawAvailability && typeof rawAvailability === "object" ?
      Object.entries(rawAvailability).map(([name, value]) => ({ name, ...(typeof value === "object" ? value : { available: Boolean(value) }) })) : [];
  const unavailable = name => {
    const row = toolAvailability.find(item => item.name === name || item.tool === name || item.operation === name);
    return row && (row.available === false || row.state === "unavailable" || row.status === "unavailable") ? row.reason || row.message || "provider reports unavailable" : null;
  };
  await call("binary_overview", argumentsFor(toolMap.get("binary_overview")), 1200000);
  const procedures = await call("list_procedures", argumentsFor(toolMap.get("list_procedures")), 600000);
  const candidates = procedureCandidates(procedures);
  const priorities = [/UIApplicationMain/i, /application.*didFinishLaunching/i, /scene.*willConnect/i, /main$/i, /_main$/i, /AppDelegate/i, /SceneDelegate/i, /SwiftUI.*App/i, /URLSession/i, /WKWebView/i, /login|auth|network|api/i];
  candidates.sort((a, b) => {
    const score = value => {
      const index = priorities.findIndex(pattern => pattern.test(value.name));
      return index < 0 ? priorities.length + 1 : index;
    };
    return score(a) - score(b);
  });
  const selected = candidates.slice(0, 6);
  await fs.writeFile("reports/ghidra-selected-procedures.json", JSON.stringify(selected, null, 2), { mode: 0o600 });

  let analyzed = 0;
  const analysisUnavailable = unavailable("analyze_function");
  for (const item of (analysisUnavailable ? [] : selected)) {
    try {
      const result = await call("analyze_function", argumentsFor(toolMap.get("analyze_function"), {
        procedure: item.procedure,
        detail: "complete"
      }), 600000);
      await fs.writeFile(`reports/ghidra-function-${String(++analyzed).padStart(2, "0")}.json`, JSON.stringify({
        selected: item,
        result
      }, null, 2), { mode: 0o600 });
    } catch (error) {
      await fs.appendFile("reports/limitations.txt", `Function ${item.procedure}: ${error.message}\n`);
    }
  }

  for (const [name, seed] of [
    ["get_objc_classes", { pattern: "" }],
    ["get_objc_protocols", {}],
    ["analyze_swift_types", {}],
    ["inspect_native_dispatch_metadata", {}]
  ]) {
    if (!toolMap.has(name)) continue;
    try { await call(name, argumentsFor(toolMap.get(name), seed), 300000); }
    catch (error) { await fs.appendFile("reports/limitations.txt", `${name}: ${error.message}\n`); }
  }

  const summary = {
    provider: "ghidra",
    binary: binaryPath,
    toolCount: catalog.tools.length,
    procedureCandidates: candidates.length,
    functionDossiers: analyzed,
    toolAvailability,
    auxiliaryAnalyses: ["get_objc_classes", "get_objc_protocols", "analyze_swift_types", "inspect_native_dispatch_metadata"].filter(name => outputs.has(name)),
    limitations: [
      ...(candidates.length ? [] : ["REA returned no procedure identities from list_procedures."]),
      ...(analysisUnavailable ? [`analyze_function unavailable: ${analysisUnavailable}`] : [])
    ]
  };
  await fs.writeFile("reports/ghidra-session-summary.json", JSON.stringify(summary, null, 2), { mode: 0o600 });
  console.log("Persistent REA/Ghidra analysis session completed.");
} finally {
  if (opened) {
    try { await call("close_binary", argumentsFor(toolMap.get("close_binary") || { inputSchema: { properties: {}, required: [] } }), 120000); }
    catch (error) { await fs.appendFile("reports/limitations.txt", `close_binary cleanup: ${error.message}\n`); }
  }
  await client.close().catch(() => {});
  await transport.close().catch(() => {});
}
