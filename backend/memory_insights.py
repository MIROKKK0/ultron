"""Read-only lexical diagnostics for ULTRON's private memory graph."""
from __future__ import annotations

import re
import unicodedata
from collections import Counter
from typing import Any


def _tokens(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFKC", str(value)).casefold()
    return set(re.findall(r"[a-zà-ú0-9]{3,}", normalized))


def analyze_memories(memories: list[dict[str, Any]], degrees: dict[int, int]) -> dict[str, Any]:
    """Return evidence-backed hints; never writes, merges, or labels hypotheses as facts."""
    kinds = ("episodic", "semantic", "procedural")
    counts = Counter(str(item.get("kind", "")) for item in memories)
    gaps = [
        {"type": "missing_memory_kind", "kind": kind,
         "evidence": "Nenhuma memória deste tipo foi encontrada no conjunto analisado."}
        for kind in kinds if counts[kind] == 0
    ]
    orphan_ids = [int(item["id"]) for item in memories
                  if degrees.get(int(item["id"]), 0) == 0]
    if orphan_ids:
        gaps.append({
            "type": "unconnected_memories", "memory_ids": orphan_ids[:50],
            "evidence": "Memórias sem relações explícitas de proveniência no grafo.",
        })

    low_confidence = [
        {"memory_id": int(item["id"]), "confidence": float(item.get("confidence", 0))}
        for item in memories if float(item.get("confidence", 0)) < 0.55
    ][:50]

    duplicates = []
    token_sets = [(item, _tokens(str(item.get("content", "")))) for item in memories]
    for index, (left, left_tokens) in enumerate(token_sets):
        if not left_tokens:
            continue
        for right, right_tokens in token_sets[index + 1:]:
            if not right_tokens:
                continue
            union = left_tokens | right_tokens
            score = len(left_tokens & right_tokens) / len(union)
            if score >= 0.72:
                duplicates.append({
                    "memory_ids": [int(left["id"]), int(right["id"])],
                    "similarity": round(score, 4),
                    "method": "token_jaccard",
                    "status": "candidate_review_only",
                })
                if len(duplicates) >= 50:
                    break
        if len(duplicates) >= 50:
            break

    return {
        "counts_by_kind": {kind: int(counts[kind]) for kind in kinds},
        "duplicate_candidates": duplicates,
        "knowledge_gaps": gaps,
        "low_confidence_memories": low_confidence,
        "analysis_limits": [
            "Similaridade lexical não comprova duplicidade semântica.",
            "Ausência de relações explícitas não prova ausência de conhecimento.",
            "Lacunas são sinais para revisão, não conclusões.",
        ],
    }
