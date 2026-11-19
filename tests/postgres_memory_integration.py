"""Real PostgreSQL integration checks for ULTRON memory retrieval.

Runs only against the disposable PostgreSQL service created by GitHub Actions.
It never connects to the Render production database.
"""
from __future__ import annotations

import os
import uuid

import psycopg
from psycopg.rows import dict_row
from psycopg import sql

from backend.memory_system import MemoryStore
from backend.local_vector_index import LocalVectorIndex


def main() -> None:
    dsn = os.environ["ULTRON_TEST_DATABASE_URL"]
    schema = "ultron_it_" + uuid.uuid4().hex
    with psycopg.connect(dsn, row_factory=dict_row) as db:
        db.execute(sql.SQL("CREATE SCHEMA {}").format(sql.Identifier(schema)))
        try:
            db.execute(sql.SQL("SET search_path TO {}").format(sql.Identifier(schema)))
            store = MemoryStore(db)
            store.initialize()

            first = store.add(
                "ci-owner-a", "semantic",
                "ULTRON mantém memória neural local independente",
                "postgres-ci", 0.95,
            )
            store.add(
                "ci-owner-b", "semantic",
                "Memória privada de outra instalação",
                "postgres-ci", 0.90,
            )

            # Exercises the nullable kind parameter that previously failed
            # with psycopg.errors.IndeterminateDatatype.
            unfiltered = store.retrieve("ci-owner-a", "memória neural", kind=None)
            assert any(row["id"] == first for row in unfiltered), unfiltered
            filtered = store.retrieve("ci-owner-a", "memória neural", kind="semantic")
            assert any(row["id"] == first for row in filtered), filtered
            assert all(row["kind"] == "semantic" for row in filtered)

            index = LocalVectorIndex(db)
            index.initialize()
            index.upsert(
                "ci-owner-a", first,
                "ULTRON mantém memória neural local independente",
            )

            # Exercises LocalVectorIndex.search's nullable type filter on
            # PostgreSQL and verifies owner isolation.
            results = index.search(
                "ci-owner-a", "memória neural ULTRON", kind=None, limit=8
            )
            assert results and results[0]["id"] == first, results
            assert all(row["id"] != 2 for row in results), results

            typed = index.search(
                "ci-owner-a", "memória neural ULTRON",
                kind="semantic", limit=8,
            )
            assert typed and all(row["kind"] == "semantic" for row in typed)
            print(
                "PostgreSQL memory integration passed: "
                "MemoryStore nullable filter, vector nullable filter, "
                "typed filter, and owner isolation."
            )
        finally:
            db.execute(sql.SQL("DROP SCHEMA {} CASCADE").format(sql.Identifier(schema)))


if __name__ == "__main__":
    main()
