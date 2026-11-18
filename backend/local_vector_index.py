"""Dependency-free local sparse-vector index for installation-scoped memories.

Vectors are deterministic lexical feature vectors, not neural embeddings.
The interface is replaceable by a genuinely local embedding model later.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
from datetime import datetime, timezone
from typing import Any


class LocalSparseVectorizer:
    VERSION = "word-charhash-v1"

    def __init__(self, dimensions: int = 4096, max_features: int = 256) -> None:
        if dimensions < 256 or max_features < 8:
            raise ValueError("Dimensões do índice inválidas.")
        self.dimensions = dimensions
        self.max_features = max_features

    def encode(self, text: str) -> dict[str, float]:
        normalized = " ".join(str(text).casefold().split())[:8000]
        words = re.findall(r"[a-zà-ú0-9]{2,}", normalized)
        features: dict[int, float] = {}
        for word in words[:512]:
            self._add(features, "w:" + word, 1.0)
            padded = f"^{word}$"
            for width in (3, 4):
                for start in range(max(0, len(padded) - width + 1)):
                    self._add(features, f"c{width}:" + padded[start:start + width], 0.22)
        if not features:
            return {}
        norm = math.sqrt(sum(value * value for value in features.values())) or 1.0
        ranked = sorted(features.items(), key=lambda pair: (-pair[1], pair[0]))[:self.max_features]
        return {str(index): round(value / norm, 8) for index, value in ranked}

    def _add(self, vector: dict[int, float], feature: str, weight: float) -> None:
        digest = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        index = int.from_bytes(digest, "big") % self.dimensions
        vector[index] = vector.get(index, 0.0) + weight


def cosine(left: dict[str, float], right: dict[str, float]) -> float:
    if not left or not right:
        return 0.0
    dot = sum(float(value) * float(right.get(key, 0.0)) for key, value in left.items())
    left_norm = math.sqrt(sum(float(value) ** 2 for value in left.values()))
    right_norm = math.sqrt(sum(float(value) ** 2 for value in right.values()))
    if not left_norm or not right_norm:
        return 0.0
    return dot / (left_norm * right_norm)


class LocalVectorIndex:
    def __init__(self, db: Any, vectorizer: Any | None = None) -> None:
        self.db = db
        if vectorizer is not None:
            self.vectorizer = vectorizer
        elif os.getenv("ULTRON_MEMORY_ENCODER", "lexical").strip().lower() == "neural":
            from backend.local_neural_encoder import LocalNeuralEncoder
            self.vectorizer = LocalNeuralEncoder()
        else:
            self.vectorizer = LocalSparseVectorizer()

    def _execute(self, query: str, params: tuple = ()):
        if self.db.__class__.__module__.startswith("psycopg"):
            query = query.replace("?", "%s")
        return self.db.execute(query, params)

    def initialize(self) -> None:
        self._execute("""CREATE TABLE IF NOT EXISTS cognitive_memory_vectors (
            owner_id TEXT NOT NULL,
            memory_id BIGINT NOT NULL,
            vector_json TEXT NOT NULL,
            encoder_version TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            PRIMARY KEY(owner_id, memory_id)
        )""")
        self._execute("CREATE INDEX IF NOT EXISTS idx_memory_vectors_owner ON cognitive_memory_vectors(owner_id)")

    def upsert(self, owner_id: str, memory_id: int, content: str) -> None:
        vector = self.vectorizer.encode(content)
        if not vector:
            raise ValueError("Não foi possível indexar conteúdo vazio.")
        now = datetime.now(timezone.utc).isoformat()
        self._execute("DELETE FROM cognitive_memory_vectors WHERE owner_id=? AND memory_id=?",
                      (owner_id, int(memory_id)))
        self._execute("""INSERT INTO cognitive_memory_vectors
            (owner_id,memory_id,vector_json,encoder_version,updated_at) VALUES(?,?,?,?,?)""",
            (owner_id, int(memory_id), json.dumps(vector, sort_keys=True, separators=(",", ":")),
             self.vectorizer.VERSION, now))

    def delete(self, owner_id: str, memory_id: int) -> None:
        self._execute("DELETE FROM cognitive_memory_vectors WHERE owner_id=? AND memory_id=?",
                      (owner_id, int(memory_id)))

    def index_missing(self, owner_id: str, *, limit: int = 5000) -> int:
        if not 1 <= int(limit) <= 10000:
            raise ValueError("limit deve ficar entre 1 e 10000.")
        rows = self._execute("""SELECT m.id,m.content FROM cognitive_memories m
            LEFT JOIN cognitive_memory_vectors v
              ON v.owner_id=m.owner_id AND v.memory_id=m.id
            WHERE m.owner_id=? AND (v.memory_id IS NULL OR v.encoder_version<>?)
            ORDER BY m.id LIMIT ?""", (owner_id, self.vectorizer.VERSION, int(limit))).fetchall()
        indexed = 0
        for row in rows:
            item = dict(row) if not isinstance(row, dict) else row
            try:
                self.upsert(owner_id, int(item["id"]), str(item["content"]))
                indexed += 1
            except ValueError:
                continue
        return indexed

    def search(self, owner_id: str, query: str, *, kind: str | None = None, limit: int = 8) -> list[dict]:
        if not 1 <= int(limit) <= 50:
            raise ValueError("limit deve ficar entre 1 e 50.")
        # Re-encode bounded batches when the encoder version changes. Source
        # memories remain untouched; only derived vectors are migrated.
        self.index_missing(owner_id, limit=5000)
        query_vector = self.vectorizer.encode(query)
        if not query_vector:
            return []
        rows = self._execute("""SELECT v.memory_id,v.vector_json,m.kind,m.content,m.source,
                m.confidence,m.created_at,m.last_accessed_at,m.access_count
            FROM cognitive_memory_vectors v
            JOIN cognitive_memories m ON m.id=v.memory_id AND m.owner_id=v.owner_id
            WHERE v.owner_id=? AND v.encoder_version=? AND (? IS NULL OR m.kind=?)""",
            (owner_id, self.vectorizer.VERSION, kind, kind)).fetchall()
        ranked = []
        for row in rows:
            item = dict(row) if not isinstance(row, dict) else row
            stored = json.loads(item["vector_json"])
            score = cosine(query_vector, stored) * float(item["confidence"])
            if score > 0:
                ranked.append((score, item))
        ranked.sort(key=lambda pair: (pair[0], int(pair[1]["memory_id"])), reverse=True)
        selected = []
        now = datetime.now(timezone.utc).isoformat()
        for score, item in ranked[:int(limit)]:
            self._execute("""UPDATE cognitive_memories
                SET last_accessed_at=?,access_count=access_count+1
                WHERE id=? AND owner_id=?""", (now, item["memory_id"], owner_id))
            selected.append({
                "id": int(item["memory_id"]), "kind": item["kind"], "content": item["content"],
                "source": item["source"], "confidence": float(item["confidence"]),
                "created_at": item["created_at"], "score": round(score, 6),
                "retrieval": getattr(self.vectorizer, "RETRIEVAL_KIND", "local_sparse_vector"),
                "encoder_version": self.vectorizer.VERSION,
            })
        return selected
