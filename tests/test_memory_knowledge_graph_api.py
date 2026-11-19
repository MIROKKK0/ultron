import hashlib
import os
import unittest
import uuid
from pathlib import Path

os.environ["ULTRON_DB_PATH"] = str(Path("/tmp") / "ultron-tests.sqlite3")
os.environ["ULTRON_API_TOKEN"] = "test-ultron-token"

from fastapi.testclient import TestClient
from backend.app import app, connect_db, execute

client = TestClient(app)


class MemoryKnowledgeGraphApiTests(unittest.TestCase):
    def setUp(self):
        self.installation_id = "graph-" + uuid.uuid4().hex
        self.token = uuid.uuid4().hex + uuid.uuid4().hex
        token_hash = hashlib.sha256(self.token.encode("utf-8")).hexdigest()
        with connect_db() as db:
            execute(db, "INSERT INTO installations(installation_id,token_hash,created_at,revoked_at) VALUES(?,?,?,NULL)",
                    (self.installation_id, token_hash, "2026-11-19T00:00:00+00:00"))
        self.auth = {
            "X-Installation-ID": self.installation_id,
            "X-Installation-Token": self.token,
        }

    def test_graph_contains_only_explicit_links_and_is_read_only(self):
        source = client.post("/v2/memory", headers=self.auth, json={
            "kind": "episodic", "content": "O usuário definiu a memória como privada e local",
        })
        self.assertEqual(source.status_code, 200)
        committed = client.post("/v2/memory/curate/commit", headers=self.auth, json={
            "candidate": "A memória do ULTRON permanece independente de provedores",
            "source_ids": [source.json()["id"]],
        })
        self.assertEqual(committed.status_code, 200)

        graph = client.get("/v2/memory/graph", headers=self.auth)
        self.assertEqual(graph.status_code, 200)
        payload = graph.json()
        self.assertEqual(payload["owner_scope"], "authenticated_installation")
        self.assertTrue(payload["read_only"])
        self.assertEqual(len(payload["nodes"]), 2)
        self.assertEqual(payload["edges"], [[0, 1]])
        self.assertEqual(payload["edge_details"][0]["relation"], "derived_from")
        self.assertEqual([node["degree"] for node in payload["nodes"]], [1, 1])
        self.assertEqual({node["region"] for node in payload["nodes"]}, {"episodic", "semantic"})
        self.assertTrue(all(len(node["position"]) == 3 for node in payload["nodes"]))

        with connect_db() as db:
            count = execute(db, "SELECT COUNT(*) AS total FROM cognitive_memories WHERE owner_id=?",
                            (self.installation_id,)).fetchone()["total"]
        self.assertEqual(int(count), 2)

    def test_graph_is_isolated_per_installation(self):
        other_id = "graph-other-" + uuid.uuid4().hex
        other_token = uuid.uuid4().hex + uuid.uuid4().hex
        other_hash = hashlib.sha256(other_token.encode("utf-8")).hexdigest()
        with connect_db() as db:
            execute(db, "INSERT INTO installations(installation_id,token_hash,created_at,revoked_at) VALUES(?,?,?,NULL)",
                    (other_id, other_hash, "2026-11-19T00:00:00+00:00"))
        other_auth = {"X-Installation-ID": other_id, "X-Installation-Token": other_token}
        saved = client.post("/v2/memory", headers=other_auth, json={
            "kind": "semantic", "content": "SEGREDO DE OUTRA INSTALAÇÃO",
        })
        self.assertEqual(saved.status_code, 200)

        graph = client.get("/v2/memory/graph", headers=self.auth)
        self.assertEqual(graph.status_code, 200)
        self.assertFalse(any("SEGREDO DE OUTRA INSTALAÇÃO" in node["content"]
                             for node in graph.json()["nodes"]))

    def test_graph_limit_is_bounded(self):
        response = client.get("/v2/memory/graph?limit=501", headers=self.auth)
        self.assertEqual(response.status_code, 422)

    def test_graph_initializes_typed_memory_tables_on_fresh_database(self):
        # Simulate a newly provisioned PostgreSQL database without typed-memory tables.
        with connect_db() as db:
            execute(db, "DROP TABLE IF EXISTS cognitive_memory_links")
            execute(db, "DROP TABLE IF EXISTS cognitive_memories")
        response = client.get("/v2/memory/graph", headers=self.auth)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["nodes"], [])
        with connect_db() as db:
            tables = execute(db, "SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        names = {row["name"] for row in tables}
        self.assertIn("cognitive_memories", names)
        self.assertIn("cognitive_memory_links", names)

    def test_insights_initializes_typed_memory_tables_on_fresh_database(self):
        with connect_db() as db:
            execute(db, "DROP TABLE IF EXISTS cognitive_memory_links")
            execute(db, "DROP TABLE IF EXISTS cognitive_memories")
        response = client.get("/v2/memory/insights", headers=self.auth)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["analyzed_memories"], 0)

    def test_graph_requires_installation_credentials(self):
        response = client.get("/v2/memory/graph")
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
