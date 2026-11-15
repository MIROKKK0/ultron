"""Conservative Portuguese/English intent bridge into documented FlyWire stimuli.

Only positive, unambiguous feeding/locomotion requests map to the upstream
laboratory stimuli. Negated or mixed requests remain unmapped. This is
transparent intent routing, not a trained sensory decoder.
"""
from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Literal

Stimulus = Literal["sugar", "p9"]


@dataclass(frozen=True)
class Perception:
    intent: str
    stimulus: Stimulus | None
    confidence: float
    matched_terms: tuple[str, ...]
    bridge: str = "ultron_conservative_perception_v2"

    def as_dict(self) -> dict:
        result = asdict(self)
        result["matched_terms"] = list(self.matched_terms)
        result["connectome_mapped"] = self.stimulus is not None
        result["limitation"] = (
            "Intent routing only; not a trained decoder from arbitrary language to neural activity."
        )
        return result


_RULES: tuple[tuple[str, Stimulus, tuple[str, ...]], ...] = (
    ("feeding", "sugar", (
        "açúcar", "acucar", "comida", "alimento", "alimentar", "comer",
        "food", "sugar", "feeding", "eat",
    )),
    ("locomotion", "p9", (
        "locomoção", "locomocao", "andar", "caminhar", "caminhada",
        "movimento corporal", "locomotion", "walking", "walk",
    )),
)
_NEGATION = re.compile(r"(?:\bnao\b|\bnunca\b|\bsem\b|\bevito\b|\bdispenso\b)(?:\s+\w+){0,3}\s*$", re.I)
_CLAUSE_BREAK = re.compile(r"[,;.!?]|\b(?:mas|porém|porem|entretanto)\b", re.I)


def _positive_matches(normalized: str, terms: tuple[str, ...]) -> tuple[str, ...]:
    found: list[str] = []
    for term in terms:
        pattern = re.compile(rf"(?<!\w){re.escape(term)}(?!\w)")
        for match in pattern.finditer(normalized):
            prefix = normalized[:match.start()]
            clause_start = 0
            for boundary in _CLAUSE_BREAK.finditer(prefix):
                clause_start = boundary.end()
            if _NEGATION.search(prefix[clause_start:]):
                continue
            found.append(term)
            break
    return tuple(found)


def perceive(text: str) -> dict:
    """Map only positive and unambiguous explicit intents to known experiments."""
    normalized = re.sub(r"[^\w\s,;.!?]", " ", str(text).casefold(), flags=re.UNICODE)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized:
        return Perception("empty", None, 0.0, ()).as_dict()

    candidates: list[tuple[str, Stimulus, tuple[str, ...]]] = []
    for intent, stimulus, terms in _RULES:
        matches = _positive_matches(normalized, terms)
        if matches:
            candidates.append((intent, stimulus, matches))

    if len(candidates) > 1:
        return Perception(
            "ambiguous_multiple_supported_intents", None, 0.0,
            tuple(term for _, _, matches in candidates for term in matches),
        ).as_dict()
    if len(candidates) == 1:
        intent, stimulus, matches = candidates[0]
        confidence = min(0.95, 0.65 + 0.1 * (len(matches) - 1))
        return Perception(intent, stimulus, confidence, matches).as_dict()

    return Perception(
        "general_language_or_unmapped_sensory_input", None, 0.0, ()
    ).as_dict()
