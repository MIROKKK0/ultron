# ULTRON autonomous engineering cycle

## Operating schedule and budget

- Schedule: four best-effort GitHub Actions runs per day (cron `17 */6 * * *` UTC).
- Hard workflow timeout: 35 minutes; the repair engine receives a 30-minute cycle budget.
- Per-test timeout: at most 600 seconds.
- Reproduction: at most one eligible failed workflow is re-run per cycle.
- Research discovery: up to 16 public references per cycle, from GitHub and DDGS.
- Repair diff budget: at most 30 files and 1,000 changed lines (configurable).
- Evidence retention: 30 days as a GitHub Actions artifact.
- Repair candidates are tested before and after the patch and pass a final Ruff lint gate.
- With `GEMINI_API_KEY`, Gemini proposes a structured diff; without it, the workflow uses deterministic Ruff-only fixes.
- No provider output is trusted as executable instructions. ULTRON validates paths, patch syntax, budget, tests and lint.
- GitHub Actions usage remains subject to the repository/account's available minutes and GitHub scheduling delays.

## What it can do

1. Inspect recent Actions failures, failed steps, open issues and maintenance markers.
2. Search public web/GitHub references and record URLs, snippets, dates and declared licenses where available.
3. Re-run one eligible failed workflow to test reproducibility.
4. Ask Gemini for a minimal unified diff when its secret is configured, or use Ruff safe fixes otherwise.
5. Apply a candidate only after path and patch validation; run baseline tests, post-patch tests and lint.
6. Reject candidates that fail validation or exceed the configured file/line/time budget.
7. Publish passing candidates to an isolated branch and attempt a reviewable PR.
8. Publish investigation evidence as JSON/Markdown and retain workflow artifacts.

## What it cannot honestly claim yet

- This is not a general-purpose autonomous coding model. Gemini proposes patches; it does not own ULTRON's identity, memory, policy or publication decisions.
- Ruff safe fixes cover a narrow class of Python static issues; they do not repair arbitrary Swift, backend logic, architecture or product behavior.
- Public search is not unrestricted crawling or authenticated access to private/paywalled content. Search results are untrusted data and are never executed.
- A green test suite does not prove that Gemini improved model intelligence, that the iOS app works on a physical iPhone, or that a production deployment succeeded.
- This workflow does not merge PRs, deploy releases or promote model weights.

## PR creation and activation

The workflow requests contents, issues, pull-request and Actions permissions. GitHub repository settings must also permit Actions to create pull requests. If that setting blocks it, the workflow keeps the isolated branch and records the failed PR attempt.

No direct push to `main` is performed. A candidate must be reviewable and pass required checks before merge. Authentication, memory, credentials, workflow and security-policy changes remain subject to human review. GitHub scheduled workflows only execute from the default branch; merge the investigator workflow into `main` after its checks and review to activate the schedule.
