"""Deterministic gates owned by ULTRON, never by a model provider."""
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Iterable


@dataclass(frozen=True)
class EvolutionDecision:
    accepted: bool
    publishable: bool
    reasons: tuple[str, ...]


SENSITIVE_PARTS = {".env", ".github/workflows", "secrets", "credentials",
                   "keychain", "auth", "memory.db"}


def evaluate_evolution(changed_paths: Iterable[str], *, tests_passed: bool,
                       diff_valid: bool, within_budget: bool = True,
                       human_review: bool = False) -> EvolutionDecision:
    paths = tuple(changed_paths)
    reasons = []
    if not paths:
        reasons.append("empty_change_set")
    if any(p.startswith("/") or ".." in PurePosixPath(p).parts for p in paths):
        reasons.append("path_outside_workspace")
    if any(any(part in str(PurePosixPath(p)).lower() for part in SENSITIVE_PARTS)
           for p in paths) and not human_review:
        reasons.append("human_review_required")
    if not diff_valid:
        reasons.append("invalid_patch")
    if not within_budget:
        reasons.append("execution_budget_exceeded")
    if not tests_passed:
        reasons.append("tests_not_passed")
    return EvolutionDecision(not reasons, False, tuple(reasons))
