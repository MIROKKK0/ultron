# ULTRON autonomous engineering cycle

## Operating schedule and budget

- Schedule: four best-effort GitHub Actions runs per day (23 */6 * * * UTC).
- Hard workflow timeout: 12 minutes per run; the repair engine enforces the same 720-second cycle budget internally.
- Repair test timeout: 300 seconds per test invocation.
- One reproducibility rerun at most per cycle, only for a failed run from the last 7 days and only when its run attempt is 1.
- Research discovery: at most 8 public GitHub repository references per cycle.
- Repair diff budget: at most 10 files and 300 changed lines.
- Evidence retention: 30 days as a GitHub Actions artifact.
- Each repair attempt records a Git checkpoint, base commit, elapsed time, remaining budget, decision, and rollback result in JSON/JSONL evidence.
- Recovery uses a separate 30-second restore allowance, so an exhausted experiment budget cannot disable rollback.
- No paid model API is called by this workflow. GitHub Actions usage remains subject to the repository/account's free-minute quota and GitHub limits.

## What it can do

1. Inspect recent Actions failures, failed steps, issues and maintenance markers.
2. Search the public web with DDGS and the public GitHub API (up to 8 total references per cycle); record URLs, snippets, update dates and declared licenses.
3. Re-run one eligible failed workflow to test whether the failure reproduces.
4. Run a deterministic repair experiment using Ruff's documented safe fixes only.
5. Run the repository unit-test suite before and after the candidate patch, then run a final Ruff lint gate.
6. Discard the candidate if tests/lint fail or the diff exceeds the budget.
7. Publish the candidate on a unique isolated branch, attach JSON/Markdown/patch/checkpoint/audit evidence, and attempt to open a PR.
8. Publish each investigation report to a unique run-specific branch; no force-push is used.
9. Update one investigation issue when no PR can be opened.

## What it cannot honestly claim yet

- This is not a general-purpose autonomous coding model. It does not invent arbitrary semantic fixes.
- Ruff safe fixes cover a narrow class of Python static issues; they do not repair arbitrary Swift, backend logic, architecture, or product behavior.
- Public search uses metasearch providers and GitHub's public API; it is not unrestricted crawling, authenticated browsing or access to paywalled/private content. Search results are untrusted data and are never executed.
- It does not access private credentials, secrets, personal accounts, or external systems. Authentication, memory, credential, and security changes remain human-reviewed.
- It does not deploy releases or promote model weights.

## PR creation and main

The workflow requests contents: write and pull-requests: write. GitHub repository settings must also permit Actions to create pull requests. If the setting blocks it, the workflow keeps the isolated branch and records the failed PR attempt in the investigation issue.

No direct push to main is performed. A candidate must be reviewable and pass the repository's required checks before merge. Auto-merge is not enabled by this cycle. Authentication, memory, credential, and security changes remain behind human review. Force-push and branch deletion are not part of recovery; recovery restores only tracked files changed by the current repair candidate.

## Activation

GitHub scheduled workflows only execute from the default branch. Merge the autonomous investigator PR into main after its checks pass to activate the schedule. Push/manual runs on the feature branch can validate the workflow before that.
