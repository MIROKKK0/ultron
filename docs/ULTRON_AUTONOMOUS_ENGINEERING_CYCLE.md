# ULTRON autonomous engineering cycle

## Operating schedule and budget

- Schedule: four best-effort GitHub Actions runs per day (23 */6 * * * UTC).
- Hard workflow timeout: 12 minutes per run.
- Repair test timeout: 300 seconds per test invocation.
- One reproducibility rerun at most per cycle, only for a failed run from the last 7 days and only when its run attempt is 1.
- Research discovery: at most 8 public GitHub repository references per cycle.
- Repair diff budget: at most 10 files and 300 changed lines.
- Evidence retention: 30 days as a GitHub Actions artifact.
- No paid model API is called by this workflow. GitHub Actions usage remains subject to the repository/account's free-minute quota and GitHub limits.

## What it can do

1. Inspect recent Actions failures, failed steps, issues and maintenance markers.
2. Search the public web with DDGS (up to two queries / eight results) and research public GitHub repositories; record URLs, snippets, update dates and declared licenses.
3. Re-run one eligible failed workflow to test whether the failure reproduces.
4. Run a deterministic repair experiment using Ruff's documented safe fixes only.
5. Run the repository unit-test suite before and after the candidate patch, then run a final Ruff lint gate.
6. Discard the candidate if tests/lint fail or the diff exceeds the budget.
7. Publish the candidate on a unique isolated branch, attach JSON/Markdown/patch evidence, and attempt to open a PR.
8. Update one investigation issue when no PR can be opened.

## What it cannot honestly claim yet

- This is not a general-purpose autonomous coding model. It does not invent arbitrary semantic fixes.
- Ruff safe fixes cover a narrow class of Python static issues; they do not repair arbitrary Swift, backend logic, architecture, or product behavior.
- Public search uses metasearch providers and GitHub's public API; it is not unrestricted crawling, authenticated browsing or access to paywalled/private content.
- It does not access private credentials, secrets, personal accounts, or external systems.
- It does not deploy releases or promote model weights.

## PR creation and main

The workflow requests contents: write and pull-requests: write. GitHub repository settings must also permit Actions to create pull requests. If the setting blocks it, the workflow keeps the isolated branch and records the failed PR attempt in the investigation issue.

No direct push to main is performed. A candidate must be reviewable and pass the repository's required checks before merge. Automatic main-branch changes should only be enabled after branch protection requires the full backend, iOS and regression checks; otherwise GitHub could merge a candidate without meaningful validation.

## Activation

GitHub scheduled workflows only execute from the default branch. Merge the autonomous investigator PR into main after its checks pass to activate the schedule. Push/manual runs on the feature branch can validate the workflow before that.
