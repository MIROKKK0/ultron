"""Bounded, reward-modulated associative plasticity for ULTRON.

This is an experimental computational learning layer inspired by fly mushroom
body circuits. It is not a biological simulation and never modifies FlyWire
connectome weights or language-model parameters.
"""
from __future__ import annotations

import hashlib
import math
import re
import threading
from collections import defaultdict


class SparseLexicalEncoder:
    """Deterministic sparse lexical feature encoder; not semantic embeddings."""

    def __init__(self, dimensions: int = 256, max_features: int = 48) -> None:
        if dimensions < 32 or max_features < 1 or max_features > 128:
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
    """Three-factor associations with strict feature, value and storage bounds."""

    def __init__(self, learning_rate: float = 0.08, decay: float = 0.999,
                 max_weight: float = 1.0, max_associations: int = 20000,
                 max_features_per_observation: int = 48) -> None:
        if not 0 < learning_rate <= 0.25 or not 0.9 <= decay <= 1.0:
            raise ValueError("Parâmetros de plasticidade fora dos limites.")
        if not 0 < max_weight <= 1.0 or not 1 <= max_associations <= 20000:
            raise ValueError("Limites de memória associativa inválidos.")
        if not 1 <= max_features_per_observation <= 128:
            raise ValueError("Limite de características inválido.")
        self.learning_rate = learning_rate
        self.decay = decay
        self.max_weight = max_weight
        self.max_associations = max_associations
        self.max_features_per_observation = max_features_per_observation
        self._weights: dict[tuple[int, int], float] = {}
        # Recall only visits associations connected to active input features.
        self._by_pre: dict[int, dict[int, float]] = {}
        self._lock = threading.RLock()
        self._observations = 0

    @staticmethod
    def _validated_activity(activity: dict[int, float], label: str,
                            maximum: int) -> dict[int, float]:
        if not isinstance(activity, dict) or not activity or len(activity) > maximum:
            raise ValueError(f"{label} deve conter de 1 a {maximum} características.")
        validated: dict[int, float] = {}
        for raw_index, raw_value in activity.items():
            index = int(raw_index)
            value = float(raw_value)
            if not 0 <= index < 4096 or not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"Atividade de {label} fora dos limites.")
            validated[index] = value
        return validated

    def observe(self, context: dict[int, float], outcome: dict[int, float],
                reward: float) -> dict:
        reward = float(reward)
        if not math.isfinite(reward):
            raise ValueError("Recompensa precisa ser um número finito.")
        reward = max(-1.0, min(1.0, reward))
        context = self._validated_activity(context, "Contexto", self.max_features_per_observation)
        outcome = self._validated_activity(outcome, "Resultado", self.max_features_per_observation)
        with self._lock:
            for key in list(self._weights):
                self._weights[key] *= self.decay
                if abs(self._weights[key]) < 1e-5:
                    del self._weights[key]
            delta = self.learning_rate * reward
            for pre, pre_activity in context.items():
                for post, post_activity in outcome.items():
                    key = (pre, post)
                    updated = self._weights.get(key, 0.0) + delta * pre_activity * post_activity
                    self._weights[key] = max(-self.max_weight, min(self.max_weight, updated))
            if len(self._weights) > self.max_associations:
                weakest = sorted(self._weights, key=lambda key: abs(self._weights[key]))[
                    :len(self._weights) - self.max_associations
                ]
                for key in weakest:
                    del self._weights[key]
            self._rebuild_recall_index()
            self._observations += 1
            return {"observations": self._observations, "associations": len(self._weights),
                    "reward": reward, "learning_rate": self.learning_rate,
                    "weight_bound": self.max_weight,
                    "features_context": len(context), "features_outcome": len(outcome)}

    def _rebuild_recall_index(self) -> None:
        """Build a read-optimized index keyed by active input feature."""
        by_pre: dict[int, dict[int, float]] = {}
        for (pre, post), weight in self._weights.items():
            by_pre.setdefault(pre, {})[post] = weight
        self._by_pre = by_pre

    def recall(self, context: dict[int, float], limit: int = 8) -> list[dict]:
        if not context:
            return []
        context = self._validated_activity(context, "Contexto", self.max_features_per_observation)
        scores: dict[int, float] = defaultdict(float)
        with self._lock:
            for pre, activity in context.items():
                for post, weight in self._by_pre.get(pre, {}).items():
                    scores[post] += activity * weight
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
            self._rebuild_recall_index()
            self._observations = max(0, int(state.get("observations", 0)))


LEXICAL_ENCODER = SparseLexicalEncoder()
ASSOCIATIVE_MEMORY = RewardModulatedAssociativeMemory()
