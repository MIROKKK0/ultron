"""Promotion gate for measurable self-improvement experiments."""
from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True)
class Evaluation:
    score: float
    regressions: int
    safety_failures: int
    latency_ms: float = 0.0

def compare_candidate(baseline: Evaluation, candidate: Evaluation,
                      min_gain: float = 0.01, max_latency_ratio: float = 1.25) -> dict:
    if min_gain < 0 or max_latency_ratio < 1:
        raise ValueError("Limites de promoção inválidos.")
    gain = candidate.score - baseline.score
    latency_ok = (baseline.latency_ms <= 0 or candidate.latency_ms <= baseline.latency_ms * max_latency_ratio)
    passed = (gain >= min_gain and candidate.regressions == 0 and
              candidate.safety_failures == 0 and latency_ok)
    return {"promotion": "eligible_for_pr" if passed else "rejected",
            "baseline_score": baseline.score, "candidate_score": candidate.score,
            "gain": round(gain, 6), "regressions": candidate.regressions,
            "safety_failures": candidate.safety_failures, "latency_ok": latency_ok,
            "reason": "melhora mínima comprovada sem regressões" if passed else "não atingiu todos os gates"}
