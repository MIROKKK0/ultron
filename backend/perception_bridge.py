"""Conservative Portuguese/English intent bridge into documented FlyWire stimuli.

This is a routing adapter, not a natural-language understanding model. It maps
only explicit feeding and locomotion requests to the two upstream experiments
that the bundled FlyWire simulator actually documents. Other text remains on
ULTRON's lightweight FlyBrain control circuit and is never misrepresented as a
full-connectome stimulus.
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
    bridge: str = "ultron_conservative_perception_v1"

    def as_dict(self) -> dict:
        result = asdict(self)
        result["matched_terms"] = list(self.matched_terms)
        result["connectome_mapped"] = self.stimulus is not None
        result["limitation"] = (
            "Intent routing only; it does not decode arbitrary language into neural activity."
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


def perceive(text: str) -> dict:
    """Classify only explicitly supported intents; otherwise report unmapped."""
    normalized = re.sub(r"[^\w\s]", " ", str(text).casefold(), flags=re.UNICODE)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if not normalized:
        return Perception("empty", None, 0.0, ()).as_dict()

    for intent, stimulus, terms in _RULES:
        matches = tuple(term for term in terms if re.search(
            rf"(?<!\w){re.escape(term)}(?!\w)", normalized
        ))
        if matches:
            confidence = min(0.95, 0.65 + 0.1 * (len(matches) - 1))
            return Perception(intent, stimulus, confidence, matches).as_dict()

    return Perception(
        "general_language_or_unmapped_sensory_input", None, 0.0, ()
    ).as_dict()
