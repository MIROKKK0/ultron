import { promises as fs } from "node:fs";
import { promisify } from "node:util";
import { assertPublicHost } from "./site-network-policy.mjs";
import { chromium } from "playwright";

const execFile = promisify((await import("node:child_process")).execFile);
const job = JSON.parse(await fs.readFile(process.env.JOB_FILE || "job.json", "utf8"));
const target = new URL(job.target_url || "");
if (target.protocol !== "https:" || !target.hostname || target.username || target.password || (target.port && target.port !== "443")) {
  throw new Error("Only public HTTPS URLs on the default port are accepted.");
}
await assertPublicHost(target.hostname);
const reportDir = "reports";
await fs.mkdir(reportDir, { recursive: true });
const endpoint = (process.env.REA_CDP_ENDPOINT || "http://127.0.0.1:9222").replace(/\/+$/, "");
process.env.NO_PROXY = [process.env.NO_PROXY, "127.0.0.1", "localhost"].filter(Boolean).join(",");
process.env.no_proxy = process.env.NO_PROXY;
let ready = false;
for (let i = 0; i < 60; i++) {
  try {
    const response = await execFile("curl", ["--fail", "--silent", "--show-error", endpoint + "/json/version"], {
      timeout: 3000,
      maxBuffer: 1024 * 1024
    });
    if (response.stdout) { ready = true; break; }
  } catch {}
  await new Promise(resolve => setTimeout(resolve, 500));
}
if (!ready) throw new Error("Disposable Chromium CDP endpoint did not become ready.");
console.log("Disposable Chromium CDP endpoint is ready.");
const browser = await chromium.connectOverCDP(endpoint, { timeout: 30000 });
try {
  const context = await browser.newContext({ acceptDownloads: false, ignoreHTTPSErrors: false });
  await context.route("**/*", async route => {
    const requestUrl = route.request().url();
    if (requestUrl.startsWith("data:") || requestUrl.startsWith("blob:") || requestUrl.startsWith("about:")) return route.continue();
    let parsed;
    try { parsed = new URL(requestUrl); } catch { return route.abort("blockedbyclient"); }
    if (!["http:", "https:", "ws:", "wss:"].includes(parsed.protocol)) return route.abort("blockedbyclient");
    if (route.request().isNavigationRequest() && route.request().frame().parentFrame() === null && parsed.origin !== target.origin) {
      return route.abort("blockedbyclient");
    }
    try { await assertPublicHost(parsed.hostname); return route.continue(); } catch { return route.abort("blockedbyclient"); }
  });
  const page = await context.newPage();
  await page.goto(target.href, { waitUntil: "domcontentloaded", timeout: 45000 });
  await page.waitForTimeout(3500);
  const finalUrl = new URL(page.url());
  if (finalUrl.origin !== target.origin) throw new Error("The site redirected to another origin; review and authorize that destination separately.");
  const origin = target.origin;
  const runRea = async (name, args, output) => {
    const result = await execFile("rea", [name, endpoint, ...args, "--json"], { env: process.env, timeout: 600000, maxBuffer: 128 * 1024 * 1024 });
    await fs.writeFile(output, result.stdout || result.stderr || "", { mode: 0o600 });
    return result.stdout || "";
  };
  const capturePage = async (pageURL, index) => {
    const targetsText = await runRea("list-browser-targets", ["--allowed-origins", origin], `${reportDir}/browser-targets-${index}.json`);
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
    const prefix = `${reportDir}/page-${String(index).padStart(2, "0")}`;
    await runRea("inspect-web-page", [selected.id, "--observation-ms", "1500", "--include-script-sources"], `${prefix}-inspection.json`);
    await runRea("analyze-web-bundle", [selected.id], `${prefix}-bundle-analysis.json`);
    await runRea("capture-web-screenshot", [selected.id], `${prefix}-screenshot.json`);
    return { url: pageURL, targetId: selected.id, title: await page.title() };
  };

  const pages = [];
  pages.push(await capturePage(page.url(), 1));
  const rawLinks = await page.locator("a[href]").evaluateAll(anchors => anchors.map(anchor => anchor.href));
  const routeQueue = [];
  const seen = new Set([target.href]);
  const unsafePath = /(?:logout|log-out|signout|sign-out|delete|remove|purchase|checkout|payment|subscribe|unsubscribe|cancel|confirm|submit|create)/i;
  for (const href of rawLinks) {
    try {
      const candidate = new URL(href);
      candidate.hash = "";
      candidate.search = "";
      if (candidate.origin !== target.origin || candidate.protocol !== "https:" || candidate.username || candidate.password || unsafePath.test(candidate.pathname)) continue;
      if (!seen.has(candidate.href)) {
        seen.add(candidate.href);
        routeQueue.push(candidate.href);
      }
    } catch {}
  }

  for (const routeURL of routeQueue.slice(0, 7)) {
    await page.goto(routeURL, { waitUntil: "domcontentloaded", timeout: 30000 });
    await page.waitForTimeout(1500);
    const current = new URL(page.url());
    if (current.origin !== target.origin) {
      await fs.appendFile(`${reportDir}/limitations.txt`, "A linked page redirected outside the approved origin and was skipped.\\n");
      continue;
    }
    pages.push(await capturePage(current.href, pages.length + 1));
  }

  await fs.writeFile(`${reportDir}/site-session.json`, JSON.stringify({
    requestedOrigin: origin,
    initialUrl: target.href,
    isolatedBrowserProfile: true,
    maxSameOriginPages: 8,
    pagesVisited: pages,
    crawlPolicy: "GET links only; no forms, authentication, purchases, destructive actions or cross-origin redirects"
  }, null, 2), { mode: 0o600 });
  await context.close();
} finally {
  await browser.close().catch(() => {});
}
console.log("REA site observation and bundle analysis completed.");
