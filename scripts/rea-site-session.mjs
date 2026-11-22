import { spawn } from "node:child_process";
import { promises as fs } from "node:fs";
import { promisify } from "node:util";
import dns from "node:dns/promises";
import net from "node:net";
import { chromium } from "playwright";

const execFile = promisify((await import("node:child_process")).execFile);
const job = JSON.parse(await fs.readFile(process.env.JOB_FILE || "job.json", "utf8"));
const target = new URL(job.target_url || "");
if (target.protocol !== "https:" || !target.hostname || target.username || target.password || (target.port && target.port !== "443")) {
  throw new Error("Only public HTTPS URLs on the default port are accepted.");
}
const blockedV4 = [/^0\./, /^10\./, /^127\./, /^169\.254\./, /^172\.(1[6-9]|2\d|3[01])\./, /^192\.168\./, /^192\.0\.0\./, /^198\.(18|19)\./, /^224\./, /^255\./];
function publicAddress(address) {
  const family = net.isIP(address);
  if (family === 4) return !blockedV4.some(pattern => pattern.test(address));
  if (family === 6) {
    const a = address.toLowerCase();
    return !(a === "::" || a === "::1" || a.startsWith("fc") || a.startsWith("fd") || a.startsWith("fe8") || a.startsWith("fe9") || a.startsWith("fea") || a.startsWith("feb") || a.startsWith("::ffff:127.") || a.startsWith("::ffff:10."));
  }
  return false;
}
async function assertPublicHost(host) {
  if (net.isIP(host)) {
    if (!publicAddress(host)) throw new Error("Private or reserved IP target blocked.");
    return;
  }
  const addresses = await dns.lookup(host, { all: true, verbatim: true });
  if (!addresses.length || addresses.some(item => !publicAddress(item.address))) throw new Error("DNS resolved to a private or reserved address; request blocked.");
}
await assertPublicHost(target.hostname);
const reportDir = "reports";
await fs.mkdir(reportDir, { recursive: true });
const profile = "/tmp/ultron-rea-browser-profile";
await fs.rm(profile, { recursive: true, force: true });
const child = spawn(chromium.executablePath(), [
  "--headless=new", "--remote-debugging-port=9222", "--remote-debugging-address=127.0.0.1",
  `--user-data-dir=${profile}`, "--no-first-run", "--no-default-browser-check",
  "--disable-background-networking", "--disable-extensions", "--disable-sync",
  "--disable-dev-shm-usage", "--disable-features=Translate,MediaRouter"
], { detached: true, stdio: "ignore" });
child.unref();
const endpoint = "http://127.0.0.1:9222";
let ready = false;
for (let i = 0; i < 60; i++) {
  try { const response = await fetch(endpoint + "/json/version"); if (response.ok) { ready = true; break; } } catch {}
  await new Promise(resolve => setTimeout(resolve, 500));
}
if (!ready) throw new Error("Disposable Chromium CDP endpoint did not become ready.");
const browser = await chromium.connectOverCDP(endpoint);
try {
  const context = await browser.newContext({ acceptDownloads: false, ignoreHTTPSErrors: false });
  await context.route("**/*", async route => {
    const requestUrl = route.request().url();
    if (requestUrl.startsWith("data:") || requestUrl.startsWith("blob:") || requestUrl.startsWith("about:")) return route.continue();
    let parsed;
    try { parsed = new URL(requestUrl); } catch { return route.abort("blockedbyclient"); }
    if (!["http:", "https:", "ws:", "wss:"].includes(parsed.protocol)) return route.abort("blockedbyclient");
    try { await assertPublicHost(parsed.hostname); return route.continue(); } catch { return route.abort("blockedbyclient"); }
  });
  const page = await context.newPage();
  await page.goto(target.href, { waitUntil: "domcontentloaded", timeout: 45000 });
  await page.waitForTimeout(3500);
  const finalUrl = new URL(page.url());
  if (finalUrl.origin !== target.origin) throw new Error("The site redirected to another origin; review and authorize that destination separately.");
  const origin = target.origin;
  const reaEnv = { ...process.env, REA_BROWSER_OBSERVE_ENABLED: "true", REA_BROWSER_CDP_ENDPOINTS_JSON: JSON.stringify([endpoint]), REA_BROWSER_ALLOWED_ORIGINS_JSON: JSON.stringify([origin]) };
  const runRea = async (name, args, output) => {
    const result = await execFile("rea", [name, endpoint, ...args, "--approved", "--json"], { env: reaEnv, timeout: 600000, maxBuffer: 128 * 1024 * 1024 });
    await fs.writeFile(output, result.stdout || result.stderr || "", { mode: 0o600 });
    return result.stdout || "";
  };
  const targetsText = await runRea("list-browser-targets", [], `${reportDir}/browser-targets.json`);
  const targetsJson = JSON.parse(targetsText);
  const candidates = [];
  const visit = value => {
    if (!value) return;
    if (Array.isArray(value)) return value.forEach(visit);
    if (typeof value !== "object") return;
    const url = typeof value.url === "string" ? value.url : "";
    const id = value.target_id || value.targetId || value.id;
    if (typeof id === "string" && url.startsWith(origin)) candidates.push({ id, url });
    Object.values(value).forEach(visit);
  };
  visit(targetsJson);
  const selected = candidates[0];
  if (!selected) throw new Error("REA did not discover the isolated page target at the approved origin.");
  await runRea("inspect-web-page", [selected.id, "--observation-ms", "1500"], `${reportDir}/web-inspection.json`);
  await runRea("analyze-web-bundle", [selected.id], `${reportDir}/web-bundle-analysis.json`);
  await runRea("capture-web-screenshot", [selected.id], `${reportDir}/web-screenshot.json`);
  await runRea("observe-web-session", [selected.id, "--observation-ms", "4000"], `${reportDir}/web-session-observation.json`);
  await fs.writeFile(`${reportDir}/site-session.json`, JSON.stringify({
    requestedOrigin: origin, finalUrl: finalUrl.href, cdpEndpoint: endpoint,
    isolatedBrowserProfile: true, targetId: selected.id, targetTitle: await page.title(),
    steps: ["list-browser-targets", "inspect-web-page", "analyze-web-bundle", "capture-web-screenshot", "observe-web-session"]
  }, null, 2), { mode: 0o600 });
  await context.close();
} finally {
  await browser.close().catch(() => {});
  child.kill("SIGTERM");
}
console.log("REA site observation and bundle analysis completed.");
