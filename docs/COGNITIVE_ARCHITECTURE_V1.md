# ULTRON Cognitive Architecture v1

## Goal

Evolve ULTRON from a prompt router into a measurable, tool-using cognitive agent. "Human-like" is an engineering inspiration, not a claim that the system reproduces a biological brain, has consciousness, or can be perfect.

## Evidence-based design

1. **Modular planning and coordination.** Webb, Mondal and Momennejad's 2025 Nature Communications paper proposes specialized processes for conflict monitoring, state prediction, state evaluation, task decomposition and task coordination. Its key lesson is that individually capable modules still need an explicit coordinator.
   - https://www.nature.com/articles/s41467-025-63804-5
2. **Memory is a lifecycle, not just a vector database.** The 2026 survey "Learning to remember" separates memory construction, maintenance, retrieval, consolidation, forgetting, governance and evaluation.
   - https://link.springer.com/article/10.1007/s44336-026-00044-1
3. **Agentic architecture needs evaluation and oversight.** The 2026 systematic survey covers goal formation, episodic/semantic memory, planning, continual learning, explainability, security and evaluation.
   - https://www.sciencedirect.com/science/article/pii/S0925231226014475
4. **Neuro-symbolic hybrid.** Neural models help with language and pattern recognition; deterministic code is better for constraints, arithmetic, authorization, state transitions and validation.
   - https://www.sciencedirect.com/science/article/pii/S1574013726000110

## Cognitive loop

Perceive -> attend -> retrieve -> predict/plan -> act through allowlisted tools -> observe -> critique -> consolidate -> evaluate.

- **Perception:** normalize the request, identify intent, constraints, freshness requirements and risk.
- **Global workspace:** maintain a small, per-request working set of goal, relevant memory, plan, evidence, tool outputs and uncertainty. The new backend cognitive workspace implements bounded attention; it does not persist user content.
- **Memory:** keep episodic, semantic and procedural stores logically separate. Retrieve with lexical/BM25 first; add embeddings only if benchmarks show a measurable gain. Every stored memory needs owner, source, timestamp, retention policy and deletion path.
- **World state:** distinguish known facts, hypotheses, stale facts and unknowns. Never treat a search snippet as verified truth.
- **Planning:** decompose goals, track dependencies, define success criteria and estimate tool/time/token budgets.
- **Action:** use a registry of allowlisted tools with schemas, timeouts, idempotency and permission gates. External/destructive actions require user approval.
- **Metacognition:** estimate confidence, detect contradictions, decide whether to research, retry, ask a question or stop. A heuristic checklist is not factual verification.
- **Learning:** store feedback and reusable procedures first. Model-weight updates require curated/licensed data, immutable evaluation sets, replay tests and rollback.

## Self-improvement gates

Observe failure -> redact and classify telemetry -> reproduce as a test -> propose a hypothesis -> implement on an isolated branch -> run unit/integration/security tests -> compare against frozen baseline -> open PR -> human review -> deploy -> health check and rollback readiness.

The agent must never edit its own evaluation set, bypass approval, expose credentials, execute arbitrary page instructions, or merge its own production changes without the authorized release gate.

## Evaluation suite

Track per-task success, factuality/source precision, tool-call correctness, memory retrieval precision/recall, calibration, refusal/permission accuracy, prompt-injection robustness, regression retention, p50/p95 latency, tokens, retries, peak RSS and cost. Version the dataset, seeds, model/config, tool versions and hashes.

Do not use language-model perplexity as a proxy for assistant quality. Keep separate benchmarks for dialogue, planning, research, coding, memory and tool execution. Require no regression on the frozen safety and capability suites before promotion.

## Resource-aware deployment

Keep the Render API process light (512 MB plan): orchestration, rate limiting, auth and small deterministic tools only. Do not load a training framework or large model into the web process. Run training/evaluation in separate GitHub Actions jobs; run local inference on iPhone only after measuring Core ML compatibility, memory, thermal behavior and tokens/second on the actual device.

## Current implementation status

- Existing ULTRON has a lightweight intent classifier, deterministic tools, a lexical memory ranker, a provider adapter, web research and a heuristic critic.
- The current cognitive cycle is not a biological brain and its specialist labels do not mean separate neural networks.
- The new working-memory component is a bounded per-request attention buffer. It is a foundation, not a complete autonomous cognitive system.
- Next milestones: pass conversation history and relevant memory to the provider; make the critic evidence-aware; isolate memories by installation; add tool budgets and typed tool registry; add frozen PT-BR eval suite; then measure safe continual improvement.
