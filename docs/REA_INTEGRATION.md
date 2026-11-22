# ULTRON + REA + isolated browser + Ghidra + xtool

## Architecture

ULTRON remains the product, identity, memory owner, planner and final decision-maker. REA is a specialist engine. xtool builds the resulting iOS project; it does not reverse-engineer or reconstruct an application by itself.

The analysis path is split by resource profile:

- **Website:** a disposable Playwright Chromium container runs as non-root `pwuser` with Chromium's sandbox and a seccomp profile (including the `pkey_mprotect` syscall needed by recent Chromium). CDP is published only on the runner's loopback and accepts only the local REA/Playwright client origins. Playwright opens the requested HTTPS origin and follows at most seven same-origin GET links (eight pages total); REA collects page, script, bundle and screenshot evidence for each visited page.
- **IPA:** the uploaded IPA is streamed to the REA bridge's temporary disk area. A GitHub Actions runner downloads it through a bearer-authenticated endpoint, validates the ZIP, extracts the app bundle and main Mach-O executable, then runs a persistent REA MCP session with the Ghidra provider.
- **ULTRON:** dispatches jobs, stores their owner/status/result in the configured database, polls the worker result and summarizes evidence. The REA bridge token and worker callback token never ship in the iOS app.
- **xtool:** remains the separate build lane. It can build the generated/edited ULTRON Xcode project into an unsigned IPA; Apple signing and device installation are separate steps.

This avoids installing Chromium or Ghidra in the small Render API process.

## Why these providers

REA's CDP inspector is passive: it attaches to an existing Chrome-family page and records DOM/resource/script/runtime evidence. It does not provide general browser control. Playwright creates the disposable browser session and navigates to the target; REA then inspects that session. The worker uses a fresh profile with no personal cookies or logged-in browser state. CDP stays bound to `127.0.0.1:9222`; it is never published as a public service.

Ghidra is the native-analysis provider selected for this project because it is open-source and can run headlessly. REA's current setup guide accepts Ghidra 12.2 with a 64-bit full JDK 25 and a `procps`-compatible `ps` on Linux; the current provider no longer accepts Ghidra 12.1.x. The workflow pins Ghidra 12.2 and verifies the release ZIP SHA-256 before use. Ghidra's headless analyzer is designed for automated import, analysis and scripts.

Hopper and IDA remain optional alternatives, not prerequisites. Hopper is commercial and IDA requires its own license/provider setup. They are not installed by this workflow.

## Render environment

The ULTRON API service needs:

- `REA_BRIDGE_URL=https://rea-bridge-vt6z.onrender.com`
- `REA_BRIDGE_TOKEN`: same 32+ character secret configured on the REA bridge service.
- `ULTRON_GITHUB_TOKEN`: fine-grained GitHub token scoped to `MIROKKK0/ultron` with Actions read/write permission. It is used only by the backend to dispatch the workflow.
- `ULTRON_GITHUB_REPO=MIROKKK0/ultron`
- `ULTRON_GITHUB_REF=main` (the default branch, where the registered worker workflow and scripts are promoted by PR #75).
- `ULTRON_WORKER_CALLBACK_TOKEN`: a separate random secret of at least 32 characters, shared with the GitHub Actions repository secret.

Set secrets in Render's service environment settings. Never commit them or put them in the IPA.

## GitHub Actions repository secrets

In `MIROKKK0/ultron` → Settings → Secrets and variables → Actions, add:

- `REA_BRIDGE_TOKEN`: exactly the same value as Render's `REA_BRIDGE_TOKEN`.
- `ULTRON_WORKER_CALLBACK_URL`: the base HTTPS URL of the deployed ULTRON API, without a trailing slash.
- `ULTRON_WORKER_CALLBACK_TOKEN`: exactly the same value as Render's `ULTRON_WORKER_CALLBACK_TOKEN`.

The workflow dispatch payload contains only a random job ID. The actual target URL or uploaded IPA ID is fetched from ULTRON through the callback-authenticated endpoint, so it is not copied into the public workflow-dispatch input.

**Release gate:** GitHub only accepts `workflow_dispatch` for a workflow file present on the repository's default branch. PR #75 must be merged into `main` to promote the current sandboxed Chromium and Ghidra 12.2/JDK 25 worker. The ULTRON API itself is deployed from `feat/ultron-core-assistant`; it dispatches the workflow on `main` using `ULTRON_GITHUB_REF=main`.

## iPhone workflow

1. Open ULTRON → Engenharia reversa.
2. For a site, enter an HTTPS URL, confirm authorization, and tap **Analisar site com REA**. The runner checks DNS and IP ranges, filters HTTP and WebSocket requests, rejects cross-origin top-level redirects, blocks service workers, opens a disposable non-root Chromium container, and runs REA's CDP inspection and bundle analysis.
3. For an IPA, select the file, tap **Enviar IPA ao REA**, then tap **Análise profunda com REA + Ghidra**. Uploads are temporary and expire after six hours.
4. ULTRON polls the job status, receives a bounded worker summary through its authenticated callback, synthesizes a Portuguese technical report with its own brain, and links to the GitHub Actions run for diagnostic logs. Raw IPA, page source, screenshots and pseudocode are not uploaded as public workflow artifacts; they remain in the ephemeral worker and are discarded when the job ends.

## Evidence and limits

- Website capture includes up to eight same-origin pages reached through ordinary GET links, DOM/resource/script evidence, static JavaScript bundle analysis and screenshots. It does not submit forms, authenticate, purchase, delete, or follow cross-origin redirects. Script sources are untrusted evidence. CDP capture is passive and starts only after the browser has navigated; it does not prove events that occurred before attachment.
- This first website worker crawls a bounded set of same-origin GET links from the landing page. It does not click buttons, submit forms, log in, or reproduce every user journey. Those require explicit Playwright scenario steps and authorization.
- The worker blocks private/reserved IP destinations at URL/DNS validation, HTTP request routing and WebSocket routing; these ranges have unit tests. Service workers are disabled during capture so they cannot bypass request interception. The browser container has no host-volume mounts, user cookies, login credentials or worker secrets. This materially reduces risk but is not a guarantee against every browser or kernel escape, and Playwright itself cautions that its Docker image is intended primarily for testing/development. Progressive web app behavior that depends on a service worker may therefore differ. Never provide credentials for an account with sensitive data.
- IPA extraction identifies the main app Mach-O executable and up to four bundled `.dylib` files. The current Ghidra worker deeply analyzes the main executable: provider overview, procedure inventory, up to six prioritized function dossiers, and available Objective-C/Swift metadata. The discovered dylibs are listed but are not yet individually decompiled. REA/Ghidra does not restore original source code. FairPlay-encrypted or otherwise protected executable sections may remain unanalyzable.
- This first native worker runs REA's Ghidra provider overview and a bounded set of function dossiers on the main executable. Full-project decompilation, separate framework/dylib passes, richer resource inventory, and evidence-to-source mapping remain additional analysis stages.
- Rebuilding a website/app means producing a clean-room implementation from observed behavior and assets that the user is authorized to reuse. It does not copy private server code, credentials, private APIs, paid assets, or protected source.
- The ULTRON repository is public. To avoid leaking a submitted IPA, app pseudocode or captured website scripts, the worker does **not** upload raw evidence as a GitHub Actions artifact. Raw worker files stay on the ephemeral runner and disappear with it; only the bounded report summary is sent over the callback token to ULTRON's job database. The GitHub run link exposes technical logs, not a downloadable IPA or source bundle.
- xtool 2.0.0-beta.1 is prerelease. Its build must independently pass ZIP, app bundle, executable and bundle-ID checks. An unsigned IPA is not signed or installed automatically.

## Acceptance checklist

- [ ] Deploy the updated REA bridge and confirm authenticated `/api/ready` returns HTTP 200 with a nonzero MCP tool count.
- [ ] Set matching bridge and worker callback secrets in Render and GitHub Actions.
- [ ] Merge PR #75 to promote the current worker workflow and scripts to the default branch.
- [ ] Verify a real public test site yields CDP targets, script evidence, bundle-analysis output and per-page screenshots on the ephemeral runner; confirm no raw artifact is published.
- [ ] Verify a non-encrypted test IPA yields a Ghidra provider doctor pass and a main Mach-O analysis report stored in ULTRON's job database; confirm no raw IPA or pseudocode artifact is published.
- [ ] Confirm failed/partial analyses report limitations instead of being marked successful.
- [ ] Run xtool separately and validate the generated unsigned IPA.
- [ ] Build any reconstruction in a separate workspace and compare it against explicit functional acceptance tests.
