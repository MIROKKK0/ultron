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
const blockedV4 = [
  /^0\\./, /^10\\./, /^100\\.(6[4-9]|[7-9]\\d|1[01]\\d|12[0-7])\\./,
  /^127\\./, /^169\\.254\\./, /^172\\.(1[6-9]|2\\d|3[01])\\./,
  /^192\\.0\\.0\\./, /^192\\.0\\.2\\./, /^192\\.88\\.99\\./, /^192\\.168\\./,
  /^198\\.(18|19)\\./, /^198\\.51\\.100\\./, /^203\\.0\\.113\\./,
  /^224\\./, /^240\\./, /^255\\./
];
function publicAddress(address) {
  const family = net.isIP(address);
  if (family === 4) return !blockedV4.some(pattern => pattern.test(address));
  if (family === 6) {
    const a = address.toLowerCase();
    if (a.startsWith("::ffff:")) {
      const mapped = a.slice(7);
      if (net.isIP(mapped) === 4) return publicAddress(mapped);
    }
    return !(a === "::" || a === "::1" || a.startsWith("fc") || a.startsWith("fd") ||
      a.startsWith("fe8") || a.startsWith("fe9") || a.startsWith("fea") ||
      a.startsWith("feb") || a.startsWith("ff") || a.startsWith("2001:db8:") ||
      a.startsWith("2001:10:") || a.startsWith("2002:"));
  }
  return false;
}
async function assertPublicHost(host) {
  const normalizedHost = host.toLowerCase().replace(/\.$/, "");
  if (normalizedHost === "localhost" || normalizedHost.endsWith(".localhost") ||
      normalizedHost.endsWith(".local") || normalizedHost.endsWith(".internal")) {
    throw new Error("Local or internal hostnames are blocked.");
  }
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
  child.kill("SIGTERM");
}
console.log("REA site observation and bundle analysis completed.");
