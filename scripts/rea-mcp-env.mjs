const REA_CHILD_ENV_KEYS = [
  "JAVA_HOME",
  "GHIDRA_INSTALL_DIR",
  "GHIDRA_HEADLESS_MAXMEM",
  "REA_GHIDRA_STARTUP_TIMEOUT_MS",
  "REA_GHIDRA_DECOMPILE_TIMEOUT_SECONDS"
];

export function buildReaMcpEnvironment(source = {}, base = {}) {
  const environment = { ...base };
  for (const key of REA_CHILD_ENV_KEYS) {
    const value = source[key];
    if (typeof value === "string" && value.length > 0) environment[key] = value;
  }
  return environment;
}
