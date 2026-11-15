# ULTRON conversational architecture

## Non-negotiable invariant: FlyBrain remains the core

The FlyBrain control circuit is not being replaced by the language model. Every public chat turn must continue to pass through `FLY_BRAIN.process(...)` before a language response is generated. Its activity, novelty, and strategy scores are passed to the iOS language layer as control context.

The neural implementation in `backend/fly_brain.py`, its LIF parameters, recurrent topology, learning boundaries, FlyWire bridge, and fail-closed behavior are intentionally unchanged by the conversational refactor.

## Request pipeline

1. **Input** — accept the user's message and apply public rate limits.
2. **Neural core** — run FlyBrain first; preserve the returned neural state and selected strategy.
3. **Policy and tools** — apply bounded feedback calibration; route explicit calculations and web-research intents to their existing deterministic/sourced tools.
4. **Language layer** — when Qwen is installed, use it on-device to formulate the natural-language response. The model receives the original question, a bounded recent conversation history, and non-private FlyBrain control signals.
5. **Streaming** — render generated tokens as they arrive; keep the composer locked during a generation to prevent overlapping requests.
6. **Failure handling** — never turn a generic decoder fallback into conversational truth, never echo it as a successful LLM answer, and report model failures clearly.
7. **Trust boundary** — tool outputs and neural telemetry are context, not instructions or proof. Never invent browsing, memory, execution, model capabilities, or full-connectome availability.

## What the current build does and does not promise

- FlyBrain remains mandatory and central; Qwen is a separate language-generation layer.
- The default Qwen3 0.6B quantized model is a small local model intended to fit constrained iPhones. It is not ChatGPT-class and may struggle with complex reasoning, long context, or nuanced instructions.
- The app streams local generation and supplies up to six recent messages with per-message bounds to preserve conversational continuity within the configured context budget.
- The neural strategy selected from FlyBrain scores guides the response format (planning, critical review, research-grounded response, or direct solving).
- The current public backend chat intentionally does not read or persist shared private conversations. A future cross-session memory feature must use per-installation identity and isolated storage; do not re-enable shared conversation tables for public chat.
- Web research is a separate source-linked tool. A language model must not claim it searched unless the tool returned sources.
- Full FlyWire loading remains opt-in, resource-gated, and fail-closed. Never enable it on Render Free or silently replace the lightweight circuit when full mode was explicitly requested.

## Acceptance checks for future work

- A chat request always calls FlyBrain before language generation.
- The response uses the original user question, not a generic fallback string.
- Follow-up turns retain relevant recent context without replaying generic processing messages.
- Generated tokens appear incrementally and only one generation runs at a time.
- Empty output, model-load errors, and generation failures produce an honest retryable message, not a fabricated answer.
- Exact deterministic operations (for example safe calculation) and sourced research remain routed through their existing tools.
- No change to FlyBrain dynamics, FlyWire resource gates, memory privacy, or approval requirements is allowed without separate tests and review.
