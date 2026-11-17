# ULTRON runtime budget — 512 MB

The hosted API must stay lightweight. The current production path uses FastAPI,
a deterministic decoder, bounded in-memory associative state and database-backed
persistence. It does not import PyTorch or load the experimental Transformer.

## Guardrails

- Keep training dependencies in `training/requirements.txt`; never install
  PyTorch in the 512 MB API service.
- Do not load a checkpoint at API import time.
- Keep task concurrency bounded; do not spawn one worker per user request.
- Bound input lengths, memory records, associative weights and generated output.
- Measure process RSS before enabling any optional model runtime.
- Keep a deterministic fallback if a model checkpoint is absent or fails to load.
- Do not run training, dataset downloads, or checkpoint conversion inside the web
  process.

## Runtime diagnostics

`GET /runtime/status` exposes process RSS and a configurable memory budget.
The default budget is 512 MB. It reports normal / high / critical pressure at
75% and 90%, respectively. This is telemetry, not a hard memory limiter; the
platform may terminate a process before it can report an out-of-memory event.

## Model integration gate

Before the tiny model can be used by the API, it must pass:
1. A reproducible Portuguese evaluation set with held-out examples.
2. A memory benchmark under realistic concurrent requests.
3. Latency and output-quality thresholds.
4. A tested unload / fallback path.
5. A checkpoint integrity and version check.

The initial from-scratch corpus is a smoke-test corpus only. It is not sufficient
for a capable general-purpose assistant.
