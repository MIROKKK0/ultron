"""Typed, scoped memory lifecycle with explicit provenance and bounded retention."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import re
from typing import Any

KINDS = {"episodic", "semantic", "procedural"}
MAX_CONTENT = 4000

@dataclass(frozen=True)
class MemoryRecord:
    id: int
    owner_id: str
    kind: str
    content: str
    source: str
    confidence: float
    created_at: str
    last_accessed_at: str
    access_count: int

class MemoryStore:
    """Uses an injected DB-API connection; caller owns connection and transaction."""
    def __init__(self, db: Any):
        self.db = db

    def _execute(self, query: str, params: tuple = ()):
        if self.db.__class__.__module__.startswith("psycopg"):
            query = query.replace("?", "%s")
        return self.db.execute(query, params)

    def initialize(self) -> None:
        primary_key = "BIGSERIAL PRIMARY KEY" if self.db.__class__.__module__.startswith("psycopg") else "INTEGER PRIMARY KEY AUTOINCREMENT"
        self._execute(f"""CREATE TABLE IF NOT EXISTS cognitive_memories (
            id {primary_key},
            owner_id TEXT NOT NULL,
            kind TEXT NOT NULL,
            content TEXT NOT NULL,
            source TEXT NOT NULL,
            confidence REAL NOT NULL,
            created_at TEXT NOT NULL,
            last_accessed_at TEXT NOT NULL,
            access_count INTEGER NOT NULL DEFAULT 0
        )""")
        self._execute("CREATE INDEX IF NOT EXISTS idx_cognitive_memory_owner_kind ON cognitive_memories(owner_id, kind, id)")
        self._execute("""CREATE TABLE IF NOT EXISTS cognitive_memory_links (
            owner_id TEXT NOT NULL,
            memory_id BIGINT NOT NULL,
            source_memory_id BIGINT NOT NULL,
            relation TEXT NOT NULL,
            created_at TEXT NOT NULL,
            PRIMARY KEY(owner_id, memory_id, source_memory_id, relation)
        )""")

    def add(self, owner_id: str, kind: str, content: str, source: str,
            confidence: float = 0.7, created_at: str | None = None) -> int:
        if not owner_id or len(owner_id) > 160 or kind not in KINDS:
            raise ValueError("Escopo ou tipo de memória inválido.")
        content = str(content).strip()
        if not content or len(content) > MAX_CONTENT:
            raise ValueError("Conteúdo de memória inválido.")
        if not 0 <= float(confidence) <= 1:
            raise ValueError("Confiança deve estar entre 0 e 1.")
        now = datetime.now(timezone.utc).isoformat()
        stored_created_at = now
        if created_at:
            try:
                parsed = datetime.fromisoformat(str(created_at).replace("Z", "+00:00"))
            except ValueError as exc:
                raise ValueError("Timestamp de origem inválido.") from exc
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            stored_created_at = parsed.astimezone(timezone.utc).isoformat()
        cursor = self._execute(
            "INSERT INTO cognitive_memories(owner_id,kind,content,source,confidence,created_at,last_accessed_at,access_count) VALUES(?,?,?,?,?,?,?,0) RETURNING id",
            (owner_id, kind, content, str(source)[:300], float(confidence), stored_created_at, now))
        inserted = cursor.fetchone()
        return int(inserted["id"] if isinstance(inserted, dict) else inserted[0])

    def retrieve(self, owner_id: str, query: str, kind: str | None = None, limit: int = 8) -> list[dict]:
        if kind is not None and kind not in KINDS:
            raise ValueError("Tipo de memória inválido.")
        rows = self._execute(
            "SELECT id,kind,content,source,confidence,created_at,last_accessed_at,access_count FROM cognitive_memories WHERE owner_id=? AND (CAST(? AS TEXT) IS NULL OR kind=?) ORDER BY id DESC LIMIT 200",
            (owner_id, kind, kind)).fetchall()
        terms = set(re.findall(r"[a-zà-ú0-9]{3,}", query.casefold()))
        scored = []
        for row in rows:
            item = dict(row) if not isinstance(row, dict) else row
            content = str(item["content"])
            tokens = set(re.findall(r"[a-zà-ú0-9]{3,}", content.casefold()))
            score = len(terms & tokens) / max(1, len(terms))
            if score > 0:
                scored.append((score * float(item["confidence"]), item))
        scored.sort(key=lambda pair: (pair[0], pair[1]["id"]), reverse=True)
        selected = [item for _, item in scored[:max(1, min(int(limit), 20))]]
        now = datetime.now(timezone.utc).isoformat()
        for item in selected:
            self._execute("UPDATE cognitive_memories SET last_accessed_at=?, access_count=access_count+1 WHERE id=? AND owner_id=?",
                            (now, item["id"], owner_id))
        return selected

    def link_sources(self, owner_id: str, memory_id: int, source_ids: list[int],
                     relation: str = "derived_from") -> None:
        if not source_ids or len(source_ids) > 20 or not relation.strip():
            raise ValueError("Referências de origem inválidas.")
        target = self._execute(
            "SELECT id FROM cognitive_memories WHERE id=? AND owner_id=?",
            (int(memory_id), owner_id),
        ).fetchone()
        if not target:
            raise ValueError("Memória de destino não pertence à instalação.")
        unique_ids = list(dict.fromkeys(int(value) for value in source_ids))
        for source_id in unique_ids:
            source = self._execute(
                "SELECT id FROM cognitive_memories WHERE id=? AND owner_id=?",
                (source_id, owner_id),
            ).fetchone()
            if not source or source_id == int(memory_id):
                raise ValueError("Memória de origem inválida.")
            self._execute(
                """INSERT INTO cognitive_memory_links
                   (owner_id,memory_id,source_memory_id,relation,created_at)
                   VALUES(?,?,?,?,?)""",
                (owner_id, int(memory_id), source_id, relation.strip()[:80],
                 datetime.now(timezone.utc).isoformat()),
            )

    def forget(self, owner_id: str, memory_id: int) -> bool:
        exists = self._execute(
            "SELECT id FROM cognitive_memories WHERE id=? AND owner_id=?",
            (int(memory_id), owner_id),
        ).fetchone()
        if not exists:
            return False
        self._execute("DELETE FROM cognitive_memory_links WHERE owner_id=? AND (memory_id=? OR source_memory_id=?)",
                      (owner_id, int(memory_id), int(memory_id)))
        cursor = self._execute("DELETE FROM cognitive_memories WHERE id=? AND owner_id=?", (int(memory_id), owner_id))
        return cursor.rowcount > 0
