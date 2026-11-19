---
name: ultron-safe-evolution
description: Evidence-based, reversible self-improvement cycle for ULTRON without external AI providers or pretrained weights.
---

# ULTRON safe evolution cycle

## Observe
- Collect failed tests, crash traces, latency, RSS, feedback counts and validation metrics.
- Treat user feedback as a signal for prioritization, not as proof that a response is correct.
- Do not upload private conversation contents to the repository or public artifacts.

## Diagnose
- Reproduce the issue and identify the owning module.
- Distinguish deterministic skill bugs, retrieval/data issues, model-quality issues, deployment issues and iOS UI issues.
- Do not claim that the small Transformer is a general language model.

## Propose
- State the expected user benefit and a measurable success metric.
- Include regression risk, memory impact, license implications and rollback plan.
- Prefer data quality, tests, retrieval and inference efficiency before increasing parameter count.

## Experiment
- Work on a branch and use only the project's own model initialized from random weights.
- Use licensed data with provenance; split by document before tokenization.
- Keep validation and test sets out of gradient updates.
- Save best validation checkpoints, tokenizer hashes, corpus hashes and reproducible configs.
- Never train or load a checkpoint inside the 512 MB production web process.

## Verify and release
- Run all relevant tests and compare the fixed benchmark to the previous baseline.
- Reject improvements that overfit, leak data, violate licenses, exceed memory budget or reduce safety.
- Open a pull request with logs and artifact checksums.
- Human review is mandatory before merge, deployment, signing or IPA publication.

## Non-goals
This skill does not create consciousness, biological neurons, unrestricted iPhone control, background permissions, or autonomous production access. It does not install third-party model weights or call hosted LLM APIs.
