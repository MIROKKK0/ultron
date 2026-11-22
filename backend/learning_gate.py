"""Regression gate for evaluated, bounded learning experiments."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LearningDecision:
    accepted: bool
    baseline_score: float
    candidate_score: float
    regressions: tuple[str, ...]
    reason: str


def evaluate_learning_candidate(
    baseline: dict[str, Any],
    candidate: dict[str, Any],
    *,
    minimum_score: float = 0.80,
    allowed_drop: float = 0.0,
) -> LearningDecision:
    if not 0.0 <= minimum_score <= 1.0 or not 0.0 <= allowed_drop <= 0.10:
        raise ValueError("Limites de avaliação inválidos.")
    base_cases = baseline.get("cases", {})
    next_cases = candidate.get("cases", {})
    if not isinstance(base_cases, dict) or not isinstance(next_cases, dict) or not base_cases:
        raise ValueError("Baseline e casos candidatos são obrigatórios.")
    if set(base_cases) != set(next_cases):
        raise ValueError("A avaliação deve usar exatamente os mesmos casos congelados.")

    regressions = []
    base_scores = []
    next_scores = []
    for case_id in sorted(base_cases):
        before = float(base_cases[case_id])
        after = float(next_cases[case_id])
        if not 0.0 <= before <= 1.0 or not 0.0 <= after <= 1.0:
            raise ValueError("Cada pontuação deve ficar entre 0 e 1.")
        base_scores.append(before)
        next_scores.append(after)
        if after + allowed_drop < before:
            regressions.append(case_id)

    base_mean = sum(base_scores) / len(base_scores)
    next_mean = sum(next_scores) / len(next_scores)
    accepted = next_mean >= minimum_score and not regressions
    reason = "passed_all_frozen_cases" if accepted else (
        "regression_detected" if regressions else "minimum_score_not_met"
    )
    return LearningDecision(accepted, round(base_mean, 4), round(next_mean, 4),
                            tuple(regressions), reason)
