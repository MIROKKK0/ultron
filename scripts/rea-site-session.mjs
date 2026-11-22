import { spawn } from "node:child_process";
import { promises as fs } from "node:fs";
import dns from "node:dns/promises";
import net from "node:net";
import { chromium } from "playwright";

const raw = process.env.TARGET_URL || "";
const target = new URL(raw);
if (target.protocol !== "https:" || !target.hostname || target.username || target.password || (target.port && target.port !== "443")) {
  throw new Error("Only public HTTPS URLs on the default port are accepted.");
}
const blockedV4 = [
  [/^0\./, "unspecified"], [/^10\./, "private"], [/^127\./, "loopback"],
  [/^169\.254\./, "link-local"], [/^172\.(1[6-9]|2\d|3[01])\./, "private"],
  [/^192\.168\./, "private"], [/^192\.0\.0\./, "special"],
  [/^198\.(18|19)\./, "benchmark"], [/^224\./, "multicast"], [/^255\./, "reserved"]
];
function publicAddress(address) {
  const family = net.isIP(address);
  if (family === 4) return !blockedV4.some(([pattern]) => pattern.test(address));
  if (family === 6) {
    const a = address.toLowerCase();
    return !(a === "::" || a === "::1" || a.startsWith("fc") || a.startsWith("fd") ||
      a.startsWith("fe8") || a.startsWith("fe9") || a.startsWith("fea") ||
      a.startsWith("feb") || a.startsWith("::ffff:127.") || a.startsWith("::ffff:10."));
  }
  return false;
}
async function assertPublicHost(host) {
  if (net.isIP(host)) {
    if (!publicAddress(host)) throw new Error("Private or reserved IP target blocked.");
    return;
  }
  const addresses = await dns.lookup(host, { all: true, verbatim: true });
  if (!addresses.length || addresses.some(item => !publicAddress(item.address))) {
    throw new Error("DNS resolved to a private or reserved address; request blocked.");
  }
}
await assertPublicHost(target.hostname);
const executable = chromium.executablePath();
const profile = "/tmp/ultron-rea-browser-profile";
await fs.rm(profile, { recursive: true, force: true });
const child = spawn(executable, [
  "--headless=new",
  "--remote-debugging-port=9222",
  "--remote-debugging-address=127.0.0.1",
  `--user-data-dir=${profile}`,
  "--no-first-run",
  "--no-default-browser-check",
  "--disable-background-networking",
  "--disable-extensions",
  "--disable-sync",
  "--disable-dev-shm-usage",
  "--disable-features=Translate,MediaRouter",
], { detached: true, stdio: "ignore" });
child.unref();
await fs.writeFile("/tmp/ultron-rea-browser.pid", String(child.pid), { mode: 0o600 });
const endpoint = "http://127.0.0.1:9222";
let ready = false;
for (let i = 0; i < 60; i++) {
  try {
    const response = await fetch(endpoint + "/json/version");
    if (response.ok) { ready = true; break; }
  } catch {}
  await new Promise(resolve => setTimeout(resolve, 500));
}
if (!ready) throw new Error("Disposable Chromium CDP endpoint did not become ready.");

const browser = await chromium.connectOverCDP(endpoint);
try {
  const context = await browser.newContext({ acceptDownloads: false, ignoreHTTPSErrors: false });
  await context.route("**/*", async route => {
    const requestUrl = route.request().url();
    if (requestUrl.startsWith("data:") || requestUrl.startsWith("blob:") || requestUrl.startsWith("about:")) {
      return route.continue();
    }
    let parsed;
    try { parsed = new URL(requestUrl); } catch { return route.abort("blockedbyclient"); }
    if (!["http:", "https:", "ws:", "wss:"].includes(parsed.protocol)) return route.abort("blockedbyclient");
    try {
      await assertPublicHost(parsed.hostname);
      return route.continue();
    } catch {
      return route.abort("blockedbyclient");
    }
  });
  const page = await context.newPage();
  await page.goto(target.href, { waitUntil: "domcontentloaded", timeout: 45000 });
  await page.waitForTimeout(3500);
  const finalUrl = new URL(page.url());
  if (finalUrl.origin !== target.origin) {
    throw new Error("The site redirected to another origin. Re-run only after explicitly reviewing that destination.");
  }
  await fs.writeFile("/tmp/ultron-rea-site.json", JSON.stringify({
    requestedOrigin: target.origin,
    finalUrl: finalUrl.href,
    cdpEndpoint: endpoint,
    browserPid: child.pid,
    isolatedProfile: true
  }, null, 2), { mode: 0o600 });
  await context.close();
} finally {
  await browser.close().catch(() => {});
}
console.log("Isolated Chromium session ready on loopback CDP for REA.");
