---
name: tdd-loop
description: Use for every bug fix or behavior change in ULTRON. Enforces a failing regression test before the smallest implementation, then full verification, while preserving FlyBrain and existing contracts.
---

# TDD loop for ULTRON

## Non-negotiable invariants

- Read `/AGENTS.md` and the relevant architecture docs before editing.
- FlyBrain remains the mandatory core and must not be bypassed, mocked in production, or replaced by an LLM/skill.
- Do not change neural weights, topology, FlyWire datasets, persistent memories, learned priorities, credentials, billing, deployment, or release configuration as part of routine TDD.
- Keep public API and persisted-data compatibility unless the task explicitly requires a migration and has a reviewed plan.
- Tests must not depend on real Apple credentials, paid APIs, or external cloud services.

## Red → Green → Refactor

1. **Map the behavior.** Trace the request from entry point through FlyBrain, language layer, storage, and API/UI boundary as relevant. Identify existing tests and the smallest observable contract.
2. **Write the regression test first.** Reproduce the bug or specify one expected behavior. The test must fail for the intended reason; capture the failure output.
3. **Implement the smallest change.** Do not broaden scope, rewrite adjacent modules, or weaken assertions to obtain a green test.
4. **Run focused tests.** Verify the new test and directly related tests.
5. **Run the project quality gates.** Discover the repository's actual test/lint/type-check commands; never invent a passing result. Run the broadest practical suite.
6. **Review the diff.** Check API compatibility, state leakage, concurrency, security, performance, and accidental changes to core behavior.
7. **Record evidence.** Report exact commands, pass/fail counts, skipped tests, and environmental blockers.

## Failure handling

- If the new test passes before the fix, it does not reproduce the issue; revise the test.
- If a test fails for environment/setup reasons, report that separately; do not call it a product regression or a pass.
- Never delete, skip, xfail, loosen, or rewrite an existing test merely to make CI green without explaining and justifying the change in the PR.
- If no safe regression test can be written, stop and propose a testability seam without changing FlyBrain semantics.

## Completion contract

A task is complete only when the behavior is covered by a meaningful test, relevant checks have been run, the diff is reviewed, and the PR describes risks and rollback. Push a branch and open a PR; do not merge or deploy.
