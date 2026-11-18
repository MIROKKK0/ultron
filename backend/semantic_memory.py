"""Optional Gemini semantic embeddings for small, tenant-scoped memory stores."""
from __future__ import annotations

import math
import os
from typing import Any

import httpx


def embed_text(text: str) -> list[float] | None:
    """Create a 768-dim vector; return None when embeddings are not configured."""
    key = os.getenv("GEMINI_API_KEY") or os.getenv("ULTRON_LLM_API_KEY")
    if not key:
        return None
    response = httpx.post(
        "https://generativelanguage.googleapis.com/v1beta/models/gemini-embedding-2:embedContent",
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        json={
            "model": "models/gemini-embedding-2",
            "content": {"parts": [{"text": text[:6000]}]},
            "output_dimensionality": 768,
        },
        timeout=httpx.Timeout(15.0, connect=5.0),
    )
    response.raise_for_status()
    payload = response.json()
    embeddings = payload.get("embeddings") or []
    values = embeddings[0].get("values") if embeddings else None
    if not isinstance(values, list) or len(values) != 768:
        raise ValueError("Gemini embedding returned an invalid vector.")
    vector = [float(value) for value in values]
    if not all(math.isfinite(value) for value in vector):
        raise ValueError("Gemini embedding contains non-finite values.")
    return vector


def cosine_similarity(left: list[float], right: list[float]) -> float:
    if len(left) != len(right) or not left:
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)


def rank_semantic(query_vector: list[float], rows: list[Any], limit: int = 8) -> list[dict[str, Any]]:
    ranked = []
    for row in rows:
        raw = row["embedding_json"]
        if not raw:
            continue
        try:
            import json
            vector = json.loads(raw)
            score = cosine_similarity(query_vector, [float(value) for value in vector])
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
        if score > 0:
            ranked.append((score, row))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [{"id": row["id"], "content": row["content"], "created_at": row["created_at"],
             "expires_at": row["expires_at"], "relevance": round(score, 4)}
            for score, row in ranked[:limit]]
