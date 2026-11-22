# ULTRON cognitive evolution v2

This milestone adds measurable, deterministic building blocks rather than claiming a human brain or autonomous model-weight training.

## Modules
- Evidence critic: checks source pointers, unsupported links, lexical overlap and conservative contradiction signals. Search snippets are not proof.
- Memory lifecycle: separate episodic, semantic and procedural records, provenance, confidence, timestamps, access counters, owner scope and deletion.
- Hierarchical planning: subtasks, dependencies, success checks and explicit success/partial-failure/blocked scenarios.
- Tool runtime: allowlisted handlers, observation records, bounded retry only for idempotent operations, no arbitrary code execution.
- Improvement gate: compare frozen baseline and candidate; require minimum gain, zero regressions, zero safety failures and bounded latency.

## Promotion cycle
1. Identify a deficiency from privacy-safe telemetry or user feedback.
2. Freeze a reproducer and regression tests before editing.
3. Run the baseline on the same cases/configuration.
4. Implement one isolated candidate change.
5. Run unit, integration, safety and regression suites.
6. Compare score, regressions, safety failures, latency and resource use.
7. Open a PR only when the gate passes; otherwise keep the candidate out of production.
8. Merge/deploy through the existing reviewed release process and retain rollback.

## Model and Portuguese
The provider adapter remains external and configurable. The current local decoder is not a general-purpose LLM. Do not claim that prompt changes train model weights. A competent Portuguese model requires a licensed PT-BR corpus, frozen evaluation sets, quantization/inference benchmarks on the actual iPhone and server, and a separate training/evaluation environment. The 512 MB Render web process must not load a training stack.

## Limitations
The critic is a triage signal, not a semantic theorem prover. Scenario simulation is qualitative, not probabilistic. Typed memory storage is a new store and must be wired to authenticated installation identity before being used for personal records. The tool registry is deliberately allowlist-only and is not permission to execute arbitrary external actions.
