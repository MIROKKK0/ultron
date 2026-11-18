"""Deterministic gates for model-proposed repository changes."""

from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Iterable, Sequence


@dataclass(frozen=True)
class EvolutionDecision:
    accepted: bool
    publishable: bool
    reasons: tuple[str, ...]


SENSITIVE_PARTS = {".env", ".github/workflows", "secrets", "credentials", "keychain", "auth", "memory.db"}


def _is_sensitive(path: str) -> bool:
    normalized = str(PurePosixPath(path)).lower()
    return any(part in normalized for part in SENSITIVE_PARTS)


def evaluate_evolution(
    changed_paths: Iterable[str],
    *,
    tests_passed: bool,
    diff_valid: bool,
    within_budget: bool = True,
    human_review: bool = False,
) -> EvolutionDecision:
    """ULTRON's local policy engine; provider output never overrides these gates."""
    paths = tuple(changed_paths)
    reasons: list[str] = []
    if not paths:
        reasons.append("empty_change_set")
    if any(path.startswith("/") or ".." in PurePosixPath(path).parts for path in paths):
        reasons.append("path_outside_workspace")
    if any(_is_sensitive(path) for path in paths) and not human_review:
        reasons.append("human_review_required")
    if not diff_valid:
        reasons.append("invalid_patch")
    if not within_budget:
        reasons.append("execution_budget_exceeded")
    if not tests_passed:
        reasons.append("tests_not_passed")
    accepted = not reasons
    # Passing local gates authorizes a reviewable PR, never a direct merge/publish.
    return EvolutionDecision(accepted=accepted, publishable=False, reasons=tuple(reasons))
