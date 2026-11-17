---
name: ultron-autonomous-evolution
description: Run bounded recurring maintenance for ULTRON: inspect health, choose one evidence-backed low-risk improvement, implement it with TDD, verify it, and open a review PR. Never self-merge or alter the neural core.
---

# ULTRON autonomous evolution

## Purpose

Improve ULTRON incrementally without destabilizing the product. This is a controlled engineering loop, not permission for unrestricted self-modification.

## Required context

At the start of every run, read:
- `/AGENTS.md`
- `.agents/skills/README.md`
- relevant architecture and decision documents
- current open PRs, recent commits, CI results, and known issues

Confirm the active core branch before work. Do not assume `main` is the correct development base. If the intended base is unclear, stop and report it.

## Evolution cycle

1. **Observe:** inspect CI failures, test gaps, crash/error reports available in the repository, dependency alerts, TODOs, and recent review feedback. Do not fabricate telemetry.
2. **Build a baseline:** run existing tests and record the exact result. Identify the real commands from project configuration.
3. **Choose one bounded improvement:** prefer a reproducible bug, flaky test, missing regression test, unsafe error path, measurable performance issue, or isolated maintainability problem. Rank by user impact, confidence, risk, and effort.
4. **Apply a deletion test:** reject changes that add abstraction, configuration, dependencies, or services without removing measurable complexity or solving a demonstrated problem.
5. **Plan:** state evidence, expected behavior, files likely affected, risk, rollback, and tests. Keep one concern per branch/PR.
6. **Implement with `tdd-loop`:** write a failing test first, make the smallest fix, and preserve existing behavior.
7. **Verify:** run focused tests, relevant full suite, lint/type checks if configured, and inspect the final diff. Compare against the baseline.
8. **Deliver:** create a descriptive branch and PR with evidence, test output, risks, and rollback. Add follow-up issues for important findings that are too risky or large.
9. **Learn:** record repeated failures as regression tests, checks, or concise documentation. Do not modify the core's learned memory or neural parameters.

## Safe autonomy budget

- Maximum one implementation PR per scheduled run.
- Documentation-only or isolated test improvements may be proposed when source-code changes are unsafe.
- If baseline tests are failing, do not stack unrelated changes; diagnose the failure or open a focused repair PR.
- If confidence is low, impact is high, or rollback is unclear, produce a report/issue only.
- Never make broad refactors, migrations, dependency upgrades, or architecture rewrites unattended.

## Hard stop conditions

Stop without editing when:
- FlyBrain processing, core state, neural topology/weights, FlyWire data, persistent user memory, or learned priorities would change.
- A change requires secrets, paid providers, new cloud infrastructure, real Apple credentials, signing, release, or IPA publication.
- CI is unavailable and the change could affect runtime behavior.
- The active branch/base is ambiguous, the working tree/branch contains unrelated work, or a conflicting PR is in progress.
- A test would need to be weakened or an existing safeguard bypassed.

## Permissions boundary

This skill may inspect repository content, run tests, create a task branch, commit/push changes, and open PRs when the connected agent has those permissions. It may not merge PRs, deploy, publish releases, alter repository permissions/secrets, or close/overwrite user work. Human approval remains required for every merge and production-impacting action.

## Cadence

Suggested cadence: once weekly, not continuously. Run only in an agent environment that explicitly supports scheduled execution and has repository access. A `SKILL.md` is an instruction set; it does not itself create a scheduler, grant GitHub permissions, or run an agent in the background. If scheduling is unavailable, run this cycle when the maintainer requests it.
