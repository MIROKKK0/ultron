"""Mandatory Drosophila-inspired spiking core for ULTRON.

This is a compact, deterministic LIF microcircuit used as ULTRON's control
center. It is inspired by the public fly-brain model and its LIF dynamics,
but it is NOT the full 138k-neuron FlyWire connectome. The upstream simulator
and its datasets are linked in THIRD_PARTY_NOTICES.md.
"""
from __future__ import annotations

import hashlib
import math
import os
import threading
from dataclasses import asdict, dataclass
from typing import Iterable

from backend.neural_learning import ASSOCIATIVE_MEMORY, LEXICAL_ENCODER

FLY_BRAIN_SOURCE = "https://github.com/eonsystemspbc/fly-brain"
FLY_BRAIN_VERSION = "0.1.0"
GROUPS = ("sensory", "memory", "attention", "action")


@dataclass(frozen=True)
class LIFParameters:
    dt_ms: float = 0.1
    tau_mem_ms: float = 20.0
    threshold: float = 1.0
    reset: float = 0.0
    leak: float = 0.0


class FlyBrainCore:
    """Small recurrent LIF network that always precedes language-model work."""

    def __init__(self, neurons_per_group: int = 12, steps: int = 40) -> None:
        if neurons_per_group < 2 or steps < 1:
            raise ValueError("Circuito neural inválido.")
        self.neurons_per_group = neurons_per_group
        self.steps = steps
        self.params = LIFParameters()
        self._lock = threading.Lock()
        self._voltage = [self.params.reset] * (neurons_per_group * len(GROUPS))
        self._trace = [0.0] * len(GROUPS)
        self._last_tokens: set[str] = set()

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return {
            token.casefold().strip(".,!?;:()[]{}\"'")[:32]
            for token in text.split()
            if len(token.strip(".,!?;:()[]{}\"'")) > 2
        }

    @staticmethod
    def _bucket(token: str, size: int) -> int:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=4).digest()
        return int.from_bytes(digest, "big") % size

    def _connections(self, source: int, target: int) -> float:
        """Deterministic sparse recurrent topology between functional groups."""
        if source == target:
            return 0.16
        if (source, target) in {(0, 1), (1, 2), (2, 3), (3, 1), (2, 0)}:
            return 0.10
        if (source, target) in {(2, 1), (3, 0)}:
            return -0.035
        return 0.0

    @staticmethod
    def _full_connectome_signal(goal: str) -> dict | None:
        """Use the real upstream brain only for its documented sensory experiments."""
        if os.getenv("ULTRON_ENABLE_FULL_FLYWIRE", "0").strip().lower() not in {"1", "true", "yes", "on"}:
            return None
        normalized = goal.casefold()
        if any(word in normalized for word in ("açúcar", "comida", "alimento", "food", "sugar")):
            stimulus = "sugar"
        elif any(word in normalized for word in ("andar", "caminhar", "locomoção", "movimento", "walk", "p9")):
            stimulus = "p9"
        else:
            return None
        from backend.flywire_runtime import simulate
        # Explicit full-brain mode must fail closed; never silently downgrade
        # to the 48-neuron demo circuit when the connectome cannot be loaded.
        return simulate(stimulus, 0.01)

    def process(self, goal: str, memories: Iterable[str] = ()) -> dict:
        goal = str(goal).strip()
        if not goal:
            raise ValueError("Informe o objetivo para o cérebro neural.")
        memory_text = " ".join(str(item)[:400] for item in list(memories)[:8])
        tokens = self._tokens(goal)
        memory_tokens = self._tokens(memory_text)
        encoded_input = LEXICAL_ENCODER.encode(goal)
        associative_recall = ASSOCIATIVE_MEMORY.recall(encoded_input, limit=8)
        association_bias = min(0.2, sum(item["activation"] for item in associative_recall) / 8.0)
        with self._lock:
            novelty = 1.0 if not self._last_tokens else (
                len(tokens - self._last_tokens) / max(1, len(tokens | self._last_tokens))
            )
            memory_match = len(tokens & memory_tokens) / max(1, len(tokens))
            sensory = [0.0] * len(GROUPS)
            sensory[0] = min(1.0, 0.2 + 0.8 * len(tokens) / 24.0)
            sensory[1] = min(1.0, memory_match + 0.15 * (1.0 - novelty) + association_bias)
            sensory[2] = min(1.0, 0.25 + 0.65 * novelty)
            sensory[3] = min(1.0, 0.15 + 0.5 * (len(tokens) > 3))

            n = self.neurons_per_group
            spikes_by_group = [0] * len(GROUPS)
            alpha = self.params.dt_ms / self.params.tau_mem_ms
            for _ in range(self.steps):
                previous = list(self._voltage)
                for group in range(len(GROUPS)):
                    for cell in range(n):
                        idx = group * n + cell
                        token_drive = sensory[group] if cell == self._bucket(
                            str(sorted(tokens)[cell % max(1, len(tokens))]) if tokens else "idle", n
                        ) else sensory[group] * 0.25
                        recurrent = 0.0
                        for source_group in range(len(GROUPS)):
                            weight = self._connections(source_group, group)
                            if weight:
                                source_start = source_group * n
                                recurrent += weight * sum(
                                    1.0 for value in previous[source_start:source_start + n]
                                    if value >= self.params.threshold
                                ) / n
                        voltage = previous[idx] + alpha * (
                            -previous[idx] + token_drive * 18.0 + recurrent * 3.0
                        )
                        if voltage >= self.params.threshold:
                            self._voltage[idx] = self.params.reset
                            spikes_by_group[group] += 1
                        else:
                            self._voltage[idx] = max(self.params.leak, voltage)

            rates = {
                name: spikes_by_group[index] / float(self.steps * n)
                for index, name in enumerate(GROUPS)
            }
            for index, name in enumerate(GROUPS):
                self._trace[index] = 0.7 * self._trace[index] + 0.3 * rates[name]
            role_scores = {
                "planner": 0.55 + self._trace[3] + self._trace[2] * 0.25,
                "solver": 0.55 + self._trace[0] + self._trace[3] * 0.2,
                "critic": 0.55 + self._trace[2] + novelty * 0.2,
                "researcher": 0.4 + self._trace[0] * 0.35 + novelty * 0.35,
            }
            full_connectome = self._full_connectome_signal(goal)
            if full_connectome and full_connectome.get("full_connectome_loaded"):
                activity = min(1.0, full_connectome["active_neurons"] / max(1, full_connectome["neurons"]))
                role_scores["solver"] += activity * 0.25
                role_scores["planner"] += activity * 0.15
                role_scores["critic"] += activity * 0.10
            self._last_tokens = tokens
            return {
                "core": "flywire_v783_with_local_control_circuit" if full_connectome and full_connectome.get("full_connectome_loaded") else "drosophila_lif_microcircuit",
                "version": FLY_BRAIN_VERSION,
                "source": FLY_BRAIN_SOURCE,
                "runtime": "upstream_pytorch_cpu" if full_connectome and full_connectome.get("full_connectome_loaded") else "local_cpu_lif",
                "is_full_connectome": bool(full_connectome and full_connectome.get("full_connectome_loaded")),
                "full_connectome": full_connectome,
                "neurons": full_connectome["neurons"] if full_connectome and full_connectome.get("full_connectome_loaded") else self.neurons_per_group * len(GROUPS),
                "simulation_steps": self.steps,
                "novelty": round(novelty, 4),
                "memory_match": round(memory_match, 4),
                "encoded_input_features": len(encoded_input),
                "associative_recall": associative_recall,
                "association_bias": round(association_bias, 4),
                "group_activity": {key: round(value, 4) for key, value in rates.items()},
                "role_scores": {key: round(value, 4) for key, value in role_scores.items()},
                "spikes": dict(zip(GROUPS, spikes_by_group)),
                "parameters": asdict(self.params),
            }


# One shared circuit keeps a short activity trace across requests.
FLY_BRAIN = FlyBrainCore()
