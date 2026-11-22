# ULTRON + REA + xtool integration

## Product boundary

The iOS app remains ULTRON. REA is a specialist reverse-engineering engine exposed through its MCP bridge; xtool is a build tool for the ULTRON Xcode project. This is one user experience, not a fork of REA or a replacement of ULTRON's identity, memory, or decision authority.

- ULTRON authenticates each iPhone installation with its existing Keychain-backed installation credential.
- ULTRON's FastAPI backend proxies the REA bridge using a server-side bearer secret. The REA secret is never placed in the IPA.
- The iOS reverse-engineering workspace discovers MCP tools, shows their descriptions and input schemas, uploads an IPA, and invokes an explicitly selected read-only analysis tool.
- xtool is pinned to 2.0.0-beta.1 in CI; XcodeGen generates the Xcode project from `project.yml`.

## Render configuration

The ULTRON API service needs these environment variables:

- `REA_BRIDGE_URL=https://rea-bridge-vt6z.onrender.com`
- `REA_BRIDGE_TOKEN`: the same long random bearer token configured as `REA_BRIDGE_TOKEN` on the REA bridge service.

Set the secret in Render's service environment settings; do not commit it, put it in the iOS app, or expose it in logs. The bridge must be deployed and its authenticated `/api/ready` endpoint must return HTTP 200 with a nonzero discovered tool count.

The REA bridge uses temporary disk-backed uploads rather than holding an entire IPA in Node.js memory. Temporary files are deleted after six hours on the next bridge startup. Render's filesystem is ephemeral; do not treat uploaded paths as durable storage.

## Using the iPhone workspace

1. Open ULTRON and tap the waveform/reverse-engineering icon.
2. Connect and discover the REA MCP catalog.
3. For a site, enter an HTTPS URL and choose a compatible REA tool. For an IPA, select the file, upload it, then choose a tool whose input schema accepts the returned file path.
4. Review the displayed schema and generated JSON arguments before running the tool.
5. Preserve the returned evidence and limitations in the analysis report.

The workspace is deliberately schema-driven: MCP tools have different required inputs, and the app does not invent missing browser targets, CDP endpoints, or binary-provider configuration.

## Capability limits and next gates

- REA website observation uses a Chrome-family browser and CDP target. A URL alone is not a browser session. The current workspace does not yet launch a per-user browser session or automatically navigate a target.
- REA's passive web inspector does not click or execute arbitrary page JavaScript. For controlled scenarios, use REA's documented scenario workflow with explicit actions and authorization.
- IPA upload is implemented, but upload is not the same as decompilation. The next step is to use the discovered Apple/package tools and validate the actual IPA tool schema. Deep native disassembly requires a supported provider such as Ghidra, Hopper, or IDA, which is not installed by this lightweight Render bridge.
- The bridge proxy currently allows only read-oriented MCP tool names. Mutating, process-control, and execution tools are denied by default.
- The analysis UI is an initial integrated workspace. Autonomous multi-step tool selection, evidence-backed reconstruction plans, generated source projects, and automatic rebuild loops remain separate acceptance gates.
- xtool 2.0.0-beta.1 is a prerelease. CI must prove an unsigned IPA exists, passes ZIP validation, contains `Payload/ULTRON.app`, has an executable, and has the expected bundle identifier. A successful build does not sign or install the IPA on the iPhone.

## Acceptance checklist

- [ ] Configure matching bridge token on both Render services.
- [ ] Authenticated REA readiness returns HTTP 200 and discovers at least one tool.
- [ ] iPhone installation can list the MCP catalog.
- [ ] IPA upload streams successfully without loading the full file into ULTRON API memory.
- [ ] At least one real IPA inspection tool returns evidence for a test IPA.
- [ ] At least one real website inspection workflow returns evidence for an authorized test site.
- [ ] Native deep analysis is enabled only after a supported provider is installed and verified.
- [ ] xtool workflow produces and validates an unsigned IPA.
- [ ] A reconstruction is built in a separate workspace and compared against explicit acceptance tests; original code, credentials, private APIs, and protected assets are not copied.
