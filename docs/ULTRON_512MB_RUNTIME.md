# ULTRON runtime budget — 512 MB

The production API remains intentionally lightweight. It keeps the existing
from-scratch intent classifier, deterministic fallback, FastAPI and bounded
associative state. It does not import PyTorch or load the experimental GPT.

## Guardrails
- Keep PyTorch in `training/generative/requirements.txt`, never in API requirements.
- Do not load a generative checkpoint during API import.
- Keep task concurrency bounded and user inputs length-limited.
- Measure process RSS before enabling optional inference.
- Keep deterministic intent routing and fallback if a checkpoint is missing.
- Never train, download datasets or convert checkpoints inside the web process.

## Telemetry
`GET /runtime/status` reports process RSS from `/proc/self/status`, a configurable
memory budget (512 MB by default) and pressure bands: high at 75%, critical at 90%.
This is telemetry, not a hard memory limiter.

## Generative model integration gate
Before enabling inference, require held-out Portuguese evaluation, quality and
safety thresholds, latency/RSS benchmarks under concurrency, checkpoint integrity,
and a tested unload/fallback path. The included training corpus is a smoke-test
corpus only and is not sufficient for a general-purpose assistant.
