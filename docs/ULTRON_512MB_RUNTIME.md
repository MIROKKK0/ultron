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


## Baseline measured in GitHub CI

The existing intent classifier (225 examples, 11 classes, 40,020-byte artifact)
was measured on a GitHub-hosted Ubuntu runner at 1,000 predictions:
- mean latency: 0.1278 ms
- p95 latency: 0.1744 ms
- process peak RSS: 15.92 MB

These are CI-runner measurements for the intent classifier only. They are not
Render production metrics and do not measure the optional PyTorch Transformer.
The new `/runtime/status` endpoint must be used after deployment to inspect the
actual web process.
