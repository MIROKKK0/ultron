import test from "node:test";
import assert from "node:assert/strict";
import { isPublicAddress } from "./site-network-policy.mjs";

test("blocks IPv4 loopback, private, link-local, shared and reserved ranges", () => {
  for (const address of [
    "0.0.0.0", "10.1.2.3", "100.64.0.1", "100.127.255.254",
    "127.0.0.1", "169.254.169.254", "172.16.0.1", "172.31.255.254",
    "192.0.0.1", "192.0.2.10", "192.88.99.1", "192.168.1.1",
    "198.18.0.1", "198.19.255.254", "198.51.100.5", "203.0.113.8",
    "224.0.0.1", "240.0.0.1", "255.255.255.255"
  ]) assert.equal(isPublicAddress(address), false, address);
});

test("blocks IPv6 local, multicast, documentation and mapped addresses", () => {
  for (const address of [
    "::", "::1", "fc00::1", "fd00::1", "fe80::1", "febf::1",
    "ff02::1", "2001:db8::1", "2001:10::1", "2002::1", "::ffff:127.0.0.1"
  ]) assert.equal(isPublicAddress(address), false, address);
});

test("allows representative public IPv4 and IPv6 addresses", () => {
  for (const address of ["8.8.8.8", "1.1.1.1", "172.32.0.1", "198.20.0.1", "2606:4700:4700::1111"]) {
    assert.equal(isPublicAddress(address), true, address);
  }
});

