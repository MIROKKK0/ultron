---
name: ultron-tdd-loop
description: Regression-first development workflow for the ULTRON backend, iOS client, skills and training code.
---

# ULTRON TDD loop

1. Inspect the affected code and its callers before editing.
2. Write the smallest regression test that fails for the reported defect.
3. Run that test and capture the failure.
4. Implement the minimum fix; preserve public APIs and existing architecture unless a migration is explicitly planned.
5. Run the focused test, then the full Python suite.
6. If training code changes, run tokenizer, model, corpus and training tests plus a short CPU smoke train.
7. If iOS code changes, run simulator and unsigned device IPA builds. A Python CI pass is not evidence that Swift compiles.
8. If API routes change, run live health, stream, fallback and memory-budget checks.
9. Report exact commands, run URLs, results, skipped tests and remaining limitations.

Never turn a skipped test into a success claim. Never hide a failing test by weakening its assertion.
