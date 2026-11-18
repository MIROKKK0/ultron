"""ULTRON's local-first, provenance-preserving memory.

Original records are immutable. Machine-generated interpretations are stored
separately, linked to their sources, and never overwrite source text.
"""
from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _canonical(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class MindCorpus:
    """Append-only personal record backed by a local SQLite database."""

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 15000")
        return conn

    def _init_db(self) -> None:
        with self._connect() as db:
            db.execute("PRAGMA journal_mode = WAL")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS mind_entries (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL CHECK(kind IN ('conversation','note','file','idea','decision','observation')),
                    speaker TEXT NOT NULL CHECK(speaker IN ('user','assistant','external','system')),
                    source TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    content_hash TEXT NOT NULL,
                    supersedes_id INTEGER REFERENCES mind_entries(id)
                );
                CREATE INDEX IF NOT EXISTS idx_mind_entries_time ON mind_entries(created_at, id);
                CREATE INDEX IF NOT EXISTS idx_mind_entries_source ON mind_entries(source);
                CREATE TABLE IF NOT EXISTS mind_derivations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entry_id INTEGER NOT NULL REFERENCES mind_entries(id),
                    agent TEXT NOT NULL,
                    derivation_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    model TEXT NOT NULL DEFAULT 'local-or-unspecified'
                );
                CREATE INDEX IF NOT EXISTS idx_mind_derivations_entry ON mind_derivations(entry_id);
                CREATE TABLE IF NOT EXISTS mind_tags (
                    entry_id INTEGER NOT NULL REFERENCES mind_entries(id),
                    tag TEXT NOT NULL,
                    agent TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY(entry_id, tag, agent)
                );
                CREATE TABLE IF NOT EXISTS mind_links (
                    source_id INTEGER NOT NULL REFERENCES mind_entries(id),
                    target_id INTEGER NOT NULL REFERENCES mind_entries(id),
                    relation TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    PRIMARY KEY(source_id, target_id, relation),
                    CHECK(source_id <> target_id)
                );
                CREATE TABLE IF NOT EXISTS mind_ledger (
                    seq INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    previous_hash TEXT NOT NULL,
                    event_hash TEXT NOT NULL UNIQUE
                );
            """)

    def _ledger(self, db: sqlite3.Connection, event_type: str, payload: dict[str, Any]) -> None:
        previous = db.execute(
            "SELECT event_hash FROM mind_ledger ORDER BY seq DESC LIMIT 1"
        ).fetchone()
        previous_hash = previous["event_hash"] if previous else "GENESIS"
        created_at = _now()
        body = _canonical({
            "event_type": event_type,
            "payload": payload,
            "created_at": created_at,
            "previous_hash": previous_hash,
        })
        digest = hashlib.sha256(body.encode("utf-8")).hexdigest()
        db.execute(
            """INSERT INTO mind_ledger
               (event_type,payload,created_at,previous_hash,event_hash)
               VALUES (?,?,?,?,?)""",
            (event_type, _canonical(payload), created_at, previous_hash, digest),
        )

    def record(
        self, content: str, *, kind: str = "conversation", speaker: str = "user",
        source: str = "ultron", supersedes_id: int | None = None,
    ) -> int:
        if not isinstance(content, str) or not content.strip():
            raise ValueError("content must be a non-empty string")
        if kind not in {"conversation", "note", "file", "idea", "decision", "observation"}:
            raise ValueError("unsupported entry kind")
        if speaker not in {"user", "assistant", "external", "system"}:
            raise ValueError("unsupported speaker")
        if supersedes_id is not None:
            with self._connect() as db:
                if not db.execute("SELECT 1 FROM mind_entries WHERE id=?", (supersedes_id,)).fetchone():
                    raise ValueError("superseded entry does not exist")
        created_at = _now()
        digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        with self._connect() as db:
            cur = db.execute(
                """INSERT INTO mind_entries
                   (kind,speaker,source,content,created_at,content_hash,supersedes_id)
                   VALUES (?,?,?,?,?,?,?)""",
                (kind, speaker, source, content, created_at, digest, supersedes_id),
            )
            entry_id = int(cur.lastrowid)
            self._ledger(db, "entry.recorded", {
                "id": entry_id, "kind": kind, "speaker": speaker,
                "source": source, "content_hash": digest,
                "supersedes_id": supersedes_id,
            })
            return entry_id

    def derive(
        self, entry_id: int, content: str, *, agent: str,
        derivation_type: str = "summary", model: str = "local-or-unspecified",
    ) -> int:
        if not content.strip() or not agent.strip():
            raise ValueError("content and agent are required")
        with self._connect() as db:
            if not db.execute("SELECT 1 FROM mind_entries WHERE id=?", (entry_id,)).fetchone():
                raise ValueError("source entry does not exist")
            cur = db.execute(
                """INSERT INTO mind_derivations
                   (entry_id,agent,derivation_type,content,created_at,model)
                   VALUES (?,?,?,?,?,?)""",
                (entry_id, agent, derivation_type, content, _now(), model),
            )
            derivation_id = int(cur.lastrowid)
            self._ledger(db, "derivation.added", {
                "id": derivation_id, "entry_id": entry_id,
                "agent": agent, "derivation_type": derivation_type,
            })
            return derivation_id

    def tag(self, entry_id: int, tag: str, *, agent: str) -> None:
        normalized = " ".join(tag.strip().lower().split())
        if not normalized or not agent.strip():
            raise ValueError("tag and agent are required")
        with self._connect() as db:
            if not db.execute("SELECT 1 FROM mind_entries WHERE id=?", (entry_id,)).fetchone():
                raise ValueError("entry does not exist")
            db.execute(
                "INSERT OR IGNORE INTO mind_tags VALUES (?,?,?,?)",
                (entry_id, normalized, agent, _now()),
            )
            self._ledger(db, "tag.added", {"entry_id": entry_id, "tag": normalized, "agent": agent})

    def link(self, source_id: int, target_id: int, *, relation: str = "related") -> None:
        if not relation.strip():
            raise ValueError("relation is required")
        with self._connect() as db:
            for entry_id in (source_id, target_id):
                if not db.execute("SELECT 1 FROM mind_entries WHERE id=?", (entry_id,)).fetchone():
                    raise ValueError("both linked entries must exist")
            db.execute(
                "INSERT OR IGNORE INTO mind_links VALUES (?,?,?,?)",
                (source_id, target_id, relation.strip(), _now()),
            )
            self._ledger(db, "link.added", {
                "source_id": source_id, "target_id": target_id, "relation": relation.strip()
            })

    def search(self, query: str, *, limit: int = 20) -> list[dict[str, Any]]:
        if not isinstance(query, str) or not query.strip():
            return []
        if not 1 <= limit <= 200:
            raise ValueError("limit must be between 1 and 200")
        needle = f"%{query.strip()}%"
        with self._connect() as db:
            rows = db.execute(
                """SELECT e.id,e.kind,e.speaker,e.source,e.content,e.created_at,
                          e.content_hash,e.supersedes_id
                   FROM mind_entries e
                   WHERE e.content LIKE ? OR e.source LIKE ?
                   ORDER BY e.created_at DESC,e.id DESC LIMIT ?""",
                (needle, needle, limit),
            ).fetchall()
            return [dict(row) for row in rows]

    def timeline(self, *, since: str | None = None, limit: int = 100) -> list[dict[str, Any]]:
        if not 1 <= limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        with self._connect() as db:
            if since:
                rows = db.execute(
                    """SELECT id,kind,speaker,source,content,created_at,content_hash,supersedes_id
                       FROM mind_entries WHERE created_at >= ?
                       ORDER BY created_at,id LIMIT ?""", (since, limit)
                ).fetchall()
            else:
                rows = db.execute(
                    """SELECT id,kind,speaker,source,content,created_at,content_hash,supersedes_id
                       FROM mind_entries ORDER BY created_at,id LIMIT ?""", (limit,)
                ).fetchall()
            return [dict(row) for row in rows]

    def context_for(self, query: str, *, limit: int = 8) -> list[dict[str, Any]]:
        """Return source entries with separately attached agent interpretations."""
        entries = self.search(query, limit=limit)
        with self._connect() as db:
            for entry in entries:
                entry["derivations"] = [
                    dict(row) for row in db.execute(
                        """SELECT agent,derivation_type,content,created_at,model
                           FROM mind_derivations WHERE entry_id=? ORDER BY id""",
                        (entry["id"],),
                    ).fetchall()
                ]
                entry["tags"] = [
                    row["tag"] for row in db.execute(
                        "SELECT tag FROM mind_tags WHERE entry_id=? ORDER BY tag",
                        (entry["id"],),
                    ).fetchall()
                ]
        return entries

    def verify_integrity(self) -> dict[str, Any]:
        with self._connect() as db:
            rows = db.execute(
                """SELECT seq,event_type,payload,created_at,previous_hash,event_hash
                   FROM mind_ledger ORDER BY seq"""
            ).fetchall()
            previous = "GENESIS"
            for row in rows:
                if row["previous_hash"] != previous:
                    return {"valid": False, "failed_seq": row["seq"], "reason": "previous_hash"}
                body = _canonical({
                    "event_type": row["event_type"],
                    "payload": json.loads(row["payload"]),
                    "created_at": row["created_at"],
                    "previous_hash": previous,
                })
                actual = hashlib.sha256(body.encode("utf-8")).hexdigest()
                if actual != row["event_hash"]:
                    return {"valid": False, "failed_seq": row["seq"], "reason": "event_hash"}
                previous = actual
            entries = db.execute(
                "SELECT id,content,content_hash FROM mind_entries ORDER BY id"
            ).fetchall()
            for entry in entries:
                actual = hashlib.sha256(entry["content"].encode("utf-8")).hexdigest()
                if actual != entry["content_hash"]:
                    return {"valid": False, "failed_entry": entry["id"], "reason": "content_hash"}
            return {"valid": True, "events_checked": len(rows), "entries_checked": len(entries)}
