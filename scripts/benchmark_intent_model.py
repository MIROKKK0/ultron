#!/usr/bin/env python3
"""Measure the lightweight ULTRON intent model's CPU latency and RSS."""
from __future__ import annotations
import argparse
import resource
import statistics
import time

from backend.intent_model import predict_intent, model_status

SAMPLES = [
    "oi ultron",
    "planeje uma melhoria no projeto",
    "melhore sua própria arquitetura",
    "qual seu status online",
    "obrigado pela ajuda",
    "conte uma história sobre dragões",
]

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--iterations", type=int, default=1000)
    args = parser.parse_args()
    if args.iterations < 1 or args.iterations > 100000:
        raise SystemExit("--iterations precisa ficar entre 1 e 100000")
    predict_intent("warmup")
    durations = []
    for index in range(args.iterations):
        started = time.perf_counter()
        predict_intent(SAMPLES[index % len(SAMPLES)])
        durations.append((time.perf_counter() - started) * 1000)
    durations.sort()
    p95 = durations[min(len(durations) - 1, int(len(durations) * 0.95))]
    rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    print({
        "model": model_status(),
        "iterations": args.iterations,
        "latency_ms_mean": round(statistics.mean(durations), 4),
        "latency_ms_p95": round(p95, 4),
        "process_peak_rss_mb": round(rss_mb, 2),
        "note": "Runner CI, not Render production metrics.",
    })
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
