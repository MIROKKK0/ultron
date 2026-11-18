"""Bounded, auditable working memory for ULTRON's cognitive cycle.

This is an operational workspace, not a simulation of human consciousness.
It keeps only per-cycle context; persistent memory remains in the database layer.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict


@dataclass(frozen=True)
class WorkspaceEntry:
    sequence: int
    kind: str
    content: str
    source: str
    confidence: float
    priority: float


class CognitiveWorkspace:
    """Small global workspace that selects salient context under a hard capacity."""

    def __init__(self, capacity: int = 7) -> None:
        if capacity < 1 or capacity > 32:
            raise ValueError("A capacidade do workspace deve ficar entre 1 e 32.")
        self.capacity = capacity
        self._entries: list[WorkspaceEntry] = []
        self._sequence = 0

    @staticmethod
    def _bounded_score(value: float, name: str) -> float:
        score = float(value)
        if not 0.0 <= score <= 1.0:
            raise ValueError(f"{name} deve estar entre 0 e 1.")
        return score

    def publish(self, kind: str, content: str, *, source: str,
                confidence: float = 1.0, priority: float = 0.5) -> WorkspaceEntry:
        kind = str(kind).strip()[:48]
        source = str(source).strip()[:80]
        content = str(content).strip()[:1600]
        if not kind or not source or not content:
            raise ValueError("kind, source e content são obrigatórios.")
        entry = WorkspaceEntry(
            sequence=self._sequence, kind=kind, content=content, source=source,
            confidence=self._bounded_score(confidence, "confidence"),
            priority=self._bounded_score(priority, "priority"),
        )
        self._sequence += 1
        self._entries.append(entry)
        if len(self._entries) > self.capacity:
            victim = min(
                range(len(self._entries)),
                key=lambda index: (
                    self._entries[index].priority * self._entries[index].confidence,
                    self._entries[index].sequence,
                ),
            )
            self._entries.pop(victim)
        return entry

    def attend(self, limit: int = 4) -> list[WorkspaceEntry]:
        """Return salient entries; recent entries win ties."""
        if limit < 1:
            raise ValueError("limit deve ser positivo.")
        ranked = sorted(
            self._entries,
            key=lambda item: (item.priority * item.confidence, item.sequence),
            reverse=True,
        )
        return ranked[: min(limit, self.capacity)]

    def snapshot(self) -> dict:
        attended = self.attend(self.capacity)
        return {
            "capacity": self.capacity,
            "size": len(self._entries),
            "attention": [asdict(item) for item in attended],
            "policy": "per_request_only; priority_times_confidence; bounded_capacity",
        }
