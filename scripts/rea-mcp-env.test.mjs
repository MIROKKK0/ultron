import assert from "node:assert/strict";
import test from "node:test";
import { buildReaMcpEnvironment } from "./rea-mcp-env.mjs";

test("forwards Ghidra runtime variables while preserving safe defaults", () => {
  const environment = buildReaMcpEnvironment(
    {
      JAVA_HOME: "/opt/jdk",
      GHIDRA_INSTALL_DIR: "/tmp/ghidra",
      GHIDRA_HEADLESS_MAXMEM: "3G",
      REA_GHIDRA_STARTUP_TIMEOUT_MS: "1800000",
      REA_GHIDRA_DECOMPILE_TIMEOUT_SECONDS: "600",
      REA_BRIDGE_TOKEN: "must-not-leak",
      ULTRON_GITHUB_TOKEN: "must-not-leak"
    },
    { PATH: "/usr/bin", HOME: "/home/runner" }
  );

  assert.equal(environment.PATH, "/usr/bin");
  assert.equal(environment.HOME, "/home/runner");
  assert.equal(environment.JAVA_HOME, "/opt/jdk");
  assert.equal(environment.GHIDRA_INSTALL_DIR, "/tmp/ghidra");
  assert.equal(environment.GHIDRA_HEADLESS_MAXMEM, "3G");
  assert.equal(environment.REA_GHIDRA_STARTUP_TIMEOUT_MS, "1800000");
  assert.equal(environment.REA_GHIDRA_DECOMPILE_TIMEOUT_SECONDS, "600");
  assert.equal(environment.REA_BRIDGE_TOKEN, undefined);
  assert.equal(environment.ULTRON_GITHUB_TOKEN, undefined);
});
