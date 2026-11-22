# ULTRON + REA + isolated browser + Ghidra + xtool

## Architecture

ULTRON remains the product, identity, memory owner, planner and final decision-maker. REA is a specialist engine. xtool builds the resulting iOS project; it does not reverse-engineer or reconstruct an application by itself.

The analysis path is split by resource profile:

- **Website:** a disposable Chromium profile is launched on an ephemeral GitHub Actions runner. Playwright opens the requested HTTPS origin and follows at most seven same-origin GET links (eight pages total); CDP is loopback-only, and REA collects page, script, bundle and screenshot evidence for each visited page.
- **IPA:** the uploaded IPA is streamed to the REA bridge's temporary disk area. A GitHub Actions runner downloads it through a bearer-authenticated endpoint, validates the ZIP, extracts the app bundle and main Mach-O executable, then runs a persistent REA MCP session with the Ghidra provider.
- **ULTRON:** dispatches jobs, stores their owner/status/result in the configured database, polls the worker result and summarizes evidence. The REA bridge token and worker callback token never ship in the iOS app.
- **xtool:** remains the separate build lane. It can build the generated/edited ULTRON Xcode project into an unsigned IPA; Apple signing and device installation are separate steps.

This avoids installing Chromium or Ghidra in the small Render API process.

## Why these providers

REA's CDP inspector is passive: it attaches to an existing Chrome-family page and records DOM/resource/script/runtime evidence. It does not provide general browser control. Playwright creates the disposable browser session and navigates to the target; REA then inspects that session. The worker uses a fresh profile with no personal cookies or logged-in browser state. CDP stays bound to `127.0.0.1:9222`; it is never published as a public service.

Ghidra is the native-analysis provider selected for this project because it is open-source and can run headlessly. REA's current setup guide documents Ghidra 12.1.x with a full JDK 21 installation and a `procps`-compatible `ps` on Linux. The workflow pins Ghidra 12.1.4 and verifies the official ZIP SHA-256 before use. Ghidra's headless analyzer is designed for automated import, analysis and scripts.

Hopper and IDA remain optional alternatives, not prerequisites. Hopper is commercial and IDA requires its own license/provider setup. They are not installed by this workflow.

## Render environment

The ULTRON API service needs:

- `REA_BRIDGE_URL=https://rea-bridge-vt6z.onrender.com`
- `REA_BRIDGE_TOKEN`: same 32+ character secret configured on the REA bridge service.
- `ULTRON_GITHUB_TOKEN`: fine-grained GitHub token scoped to `MIROKKK0/ultron` with Actions read/write permission. It is used only by the backend to dispatch the workflow.
- `ULTRON_GITHUB_REPO=MIROKKK0/ultron`
- `ULTRON_GITHUB_REF=feat/ultron-core-assistant` (the Render deployment branch; PR #73 registers the workflow file on `main`, while dispatch runs the worker from this selected branch).
- `ULTRON_WORKER_CALLBACK_TOKEN`: a separate random secret of at least 32 characters, shared with the GitHub Actions repository secret.

Set secrets in Render's service environment settings. Never commit them or put them in the IPA.

## GitHub Actions repository secrets

In `MIROKKK0/ultron` → Settings → Secrets and variables → Actions, add:

- `REA_BRIDGE_TOKEN`: exactly the same value as Render's `REA_BRIDGE_TOKEN`.
- `ULTRON_WORKER_CALLBACK_URL`: the base HTTPS URL of the deployed ULTRON API, without a trailing slash.
- `ULTRON_WORKER_CALLBACK_TOKEN`: exactly the same value as Render's `ULTRON_WORKER_CALLBACK_TOKEN`.

The workflow dispatch payload contains only a random job ID. The actual target URL or uploaded IPA ID is fetched from ULTRON through the callback-authenticated endpoint, so it is not copied into the public workflow-dispatch input.

**Release gate:** GitHub only accepts `workflow_dispatch` for a workflow file present on the repository's default branch. PR #73 registers the worker workflow and scripts on `main`; Render dispatches the worker using `ULTRON_GITHUB_REF=feat/ultron-core-assistant`, which is the selected deployment branch containing the ULTRON API routes and worker code.

## iPhone workflow

1. Open ULTRON → Engenharia reversa.
2. For a site, enter an HTTPS URL, confirm authorization, and tap **Analisar site com REA**. The runner checks the hostname, blocks private/reserved IP resolutions, rejects cross-origin redirects, opens a disposable browser profile, and runs REA's CDP inspection and bundle analysis.
3. For an IPA, select the file, tap **Enviar IPA ao REA**, then tap **Análise profunda com REA + Ghidra**. Uploads are temporary and expire after six hours.
4. ULTRON polls the job status, receives the worker summary through its authenticated callback, synthesizes a Portuguese technical report with its own brain, and links to the GitHub Actions run where the full evidence artifact is retained for 14 days.

## Evidence and limits

- Website capture includes up to eight same-origin pages reached through ordinary GET links, DOM/resource/script evidence, static JavaScript bundle analysis and screenshots. It does not submit forms, authenticate, purchase, delete, or follow cross-origin redirects. Script sources are untrusted evidence. CDP capture is passive and starts only after the browser has navigated; it does not prove events that occurred before attachment.
- This first website worker crawls a bounded set of same-origin GET links from the landing page. It does not click buttons, submit forms, log in, or reproduce every user journey. Those require explicit Playwright scenario steps and authorization.
- The worker blocks private/reserved IP destinations at URL/DNS validation and request routing, but this is not a general-purpose hostile-site sandbox. It runs in a short-lived hosted runner, uses a fresh profile, and receives no personal cookies or user credentials. Never provide credentials for an account with sensitive data.
- IPA extraction identifies the main app Mach-O executable and up to four bundled `.dylib` files. The current Ghidra worker deeply analyzes the main executable: provider overview, procedure inventory, up to six prioritized function dossiers, and available Objective-C/Swift metadata. The discovered dylibs are listed but are not yet individually decompiled. REA/Ghidra does not restore original source code. FairPlay-encrypted or otherwise protected executable sections may remain unanalyzable.
- This first native worker runs REA's Ghidra provider overview and a bounded set of function dossiers on the main executable. Full-project decompilation, separate framework/dylib passes, richer resource inventory, and evidence-to-source mapping remain additional analysis stages.
- Rebuilding a website/app means producing a clean-room implementation from observed behavior and assets that the user is authorized to reuse. It does not copy private server code, credentials, private APIs, paid assets, or protected source.
- The ULTRON repository is public. To avoid leaking a submitted IPA, app pseudocode or captured website scripts, the worker does **not** upload raw evidence as a GitHub Actions artifact. Raw worker files stay on the ephemeral runner and disappear with it; only the bounded report summary is sent over the callback token to ULTRON's job database. The GitHub run link exposes technical logs, not a downloadable IPA or source bundle.
- xtool 2.0.0-beta.1 is prerelease. Its build must independently pass ZIP, app bundle, executable and bundle-ID checks. An unsigned IPA is not signed or installed automatically.

## Acceptance checklist

- [ ] Deploy the updated REA bridge and confirm authenticated `/api/ready` returns HTTP 200 with a nonzero MCP tool count.
- [ ] Set matching bridge and worker callback secrets in Render and GitHub Actions.
- [ ] Merge/promote the worker workflow to the default branch so workflow dispatch is available.
- [ ] Verify a real public test site yields CDP targets, script evidence, bundle-analysis output and per-page screenshots on the ephemeral runner; confirm no raw artifact is published.
- [ ] Verify a non-encrypted test IPA yields a Ghidra provider doctor pass and a main Mach-O analysis report stored in ULTRON's job database; confirm no raw IPA or pseudocode artifact is published.
- [ ] Confirm failed/partial analyses report limitations instead of being marked successful.
- [ ] Run xtool separately and validate the generated unsigned IPA.
- [ ] Build any reconstruction in a separate workspace and compare it against explicit functional acceptance tests.
