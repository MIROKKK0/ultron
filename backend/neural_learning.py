"""Bounded, reward-modulated associative plasticity for ULTRON.

This is an experimental computational learning layer inspired by fly mushroom
body circuits. It is NOT a biological simulation of those circuits and does
not modify the upstream FlyWire connectome weights.
"""
from __future__ import annotations

import hashlib
import math
import re
import threading
from collections import defaultdict
from typing import Iterable


class SparseLexicalEncoder:
    """Deterministic sparse lexical feature encoder; not a semantic embedding model."""

    def __init__(self, dimensions: int = 256, max_features: int = 48) -> None:
        if dimensions < 32 or max_features < 1:
            raise ValueError("Dimensões do codificador inválidas.")
        self.dimensions = dimensions
        self.max_features = max_features

    @staticmethod
    def tokens(text: str) -> list[str]:
        words = re.findall(r"[a-zà-ú0-9]{2,}", str(text).casefold())
        return words[:512]

    def encode(self, text: str) -> dict[int, float]:
        tokens = self.tokens(text)
        counts: dict[int, int] = defaultdict(int)
        for token in tokens:
            digest = hashlib.blake2b(token.encode("utf-8"), digest_size=8).digest()
            index = int.from_bytes(digest, "big") % self.dimensions
            counts[index] += 1
        if not counts:
            return {}
        norm = math.sqrt(sum(value * value for value in counts.values())) or 1.0
        ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:self.max_features]
        return {index: round(value / norm, 6) for index, value in ranked}


class RewardModulatedAssociativeMemory:
    """Small three-factor association store: pre-activity, post-activity, reward.

    Weights are bounded and decayed. Callers must persist state explicitly if
    durable learning is required; the default instance is process-local.
    """

    def __init__(self, learning_rate: float = 0.08, decay: float = 0.999,
                 max_weight: float = 1.0, max_associations: int = 20000) -> None:
        if not 0 < learning_rate <= 0.25 or not 0.9 <= decay <= 1.0:
            raise ValueError("Parâmetros de plasticidade fora dos limites.")
        self.learning_rate = learning_rate
        self.decay = decay
        self.max_weight = max_weight
        self.max_associations = max_associations
        self._weights: dict[tuple[int, int], float] = {}
        self._lock = threading.RLock()
        self._observations = 0

    def observe(self, context: dict[int, float], outcome: dict[int, float],
                reward: float) -> dict:
        reward = max(-1.0, min(1.0, float(reward)))
        if not context or not outcome:
            raise ValueError("Contexto e resultado precisam conter atividade.")
        with self._lock:
            for key in list(self._weights):
                self._weights[key] *= self.decay
                if abs(self._weights[key]) < 1e-5:
                    del self._weights[key]
            delta = self.learning_rate * reward
            for pre, pre_activity in context.items():
                for post, post_activity in outcome.items():
                    key = (int(pre), int(post))
                    updated = self._weights.get(key, 0.0) + delta * float(pre_activity) * float(post_activity)
                    self._weights[key] = max(-self.max_weight, min(self.max_weight, updated))
            if len(self._weights) > self.max_associations:
                weakest = sorted(self._weights, key=lambda key: abs(self._weights[key]))[
                    :len(self._weights) - self.max_associations
                ]
                for key in weakest:
                    del self._weights[key]
            self._observations += 1
            return {"observations": self._observations, "associations": len(self._weights),
                    "reward": reward, "learning_rate": self.learning_rate,
                    "weight_bound": self.max_weight}

    def recall(self, context: dict[int, float], limit: int = 8) -> list[dict]:
        scores: dict[int, float] = defaultdict(float)
        with self._lock:
            for (pre, post), weight in self._weights.items():
                if pre in context:
                    scores[post] += float(context[pre]) * weight
        return [{"feature": feature, "activation": round(score, 6)}
                for feature, score in sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:max(1, min(limit, 32))]
                if score > 0]

    def state_dict(self) -> dict:
        with self._lock:
            return {"version": 1, "observations": self._observations,
                    "weights": [[pre, post, weight] for (pre, post), weight in sorted(self._weights.items())]}

    def load_state_dict(self, state: dict) -> None:
        if state.get("version") != 1 or not isinstance(state.get("weights"), list):
            raise ValueError("Estado de aprendizagem incompatível.")
        weights: dict[tuple[int, int], float] = {}
        for item in state["weights"][:self.max_associations]:
            if not isinstance(item, list) or len(item) != 3:
                continue
            pre, post, weight = int(item[0]), int(item[1]), float(item[2])
            if not (0 <= pre < 4096 and 0 <= post < 4096 and math.isfinite(weight)):
                continue
            weights[(pre, post)] = max(-self.max_weight, min(self.max_weight, weight))
        with self._lock:
            self._weights = weights
            self._observations = max(0, int(state.get("observations", 0)))


LEXICAL_ENCODER = SparseLexicalEncoder()
ASSOCIATIVE_MEMORY = RewardModulatedAssociativeMemory()
