import dns from "node:dns/promises";
import net from "node:net";

const blockedV4 = [
  /^0\./, /^10\./, /^100\.(6[4-9]|[7-9]\d|1[01]\d|12[0-7])\./,
  /^127\./, /^169\.254\./, /^172\.(1[6-9]|2\d|3[01])\./,
  /^192\.0\.0\./, /^192\.0\.2\./, /^192\.88\.99\./, /^192\.168\./,
  /^198\.(18|19)\./, /^198\.51\.100\./, /^203\.0\.113\./,
  /^224\./, /^240\./, /^255\./
];

export function isPublicAddress(address) {
  const family = net.isIP(address);
  if (family === 4) return !blockedV4.some(pattern => pattern.test(address));
  if (family === 6) {
    const value = address.toLowerCase();
    if (value.startsWith("::ffff:")) return false;
    return !(value === "::" || value === "::1" || value.startsWith("fc") || value.startsWith("fd") ||
      value.startsWith("fe8") || value.startsWith("fe9") || value.startsWith("fea") ||
      value.startsWith("feb") || value.startsWith("ff") || value.startsWith("2001:db8:") ||
      value.startsWith("2001:10:") || value.startsWith("2002:"));
  }
  return false;
}

export async function assertPublicHost(host) {
  const normalized = host.toLowerCase().replace(/^\[|\]$/g, "").replace(/\.$/, "");
  if (normalized === "localhost" || normalized.endsWith(".localhost") ||
      normalized.endsWith(".local") || normalized.endsWith(".internal")) {
    throw new Error("Local or internal hostnames are blocked.");
  }
  if (net.isIP(normalized)) {
    if (!isPublicAddress(normalized)) throw new Error("Private or reserved IP target blocked.");
    return;
  }
  const addresses = await dns.lookup(normalized, { all: true, verbatim: true });
  if (!addresses.length || addresses.some(item => !isPublicAddress(item.address))) {
    throw new Error("DNS resolved to a private or reserved address; request blocked.");
  }
}
