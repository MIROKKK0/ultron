import os
import uuid
import unittest
import hashlib
from pathlib import Path

os.environ["ULTRON_DB_PATH"] = str(Path("/tmp") / "ultron-tests.sqlite3")
os.environ["ULTRON_API_TOKEN"] = "test-ultron-token"

from fastapi.testclient import TestClient
from backend.app import app, connect_db, execute

client = TestClient(app)


class UltronMemoryV2ApiTests(unittest.TestCase):
    def setUp(self):
        self.installation_id = "memory-v2-" + uuid.uuid4().hex
        self.token = uuid.uuid4().hex + uuid.uuid4().hex
        token_hash = hashlib.sha256(self.token.encode("utf-8")).hexdigest()
        with connect_db() as db:
            execute(db, "INSERT INTO installations(installation_id,token_hash,created_at,revoked_at) VALUES(?,?,?,NULL)",
                    (self.installation_id, token_hash, "2026-11-18T00:00:00+00:00"))
        self.auth = {
            "X-Installation-ID": self.installation_id,
            "X-Installation-Token": self.token,
        }

    def test_history_import_is_explicit_scoped_and_idempotent(self):
        payload = {
            "source_export": "iphone-export-2026-11",
            "records": [
                {"role": "user", "content": "Prefiro português brasileiro", "timestamp": "2026-11-01T10:00:00Z"},
                {"role": "assistant", "content": "Vou responder em português", "timestamp": "2026-11-01T10:00:02Z"},
            ],
        }
        first = client.post("/v2/memory/import", json=payload, headers=self.auth)
        second = client.post("/v2/memory/import", json=payload, headers=self.auth)
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.json()["imported"], 2)
        self.assertEqual(second.json()["imported"], 0)
        self.assertEqual(second.json()["duplicates"], 2)
        self.assertFalse(first.json()["legacy_global_history_read"])
        results = client.get("/v2/memory?query=português", headers=self.auth)
        self.assertEqual(results.status_code, 200)
        self.assertTrue(results.json()["items"])
        self.assertTrue(any(item["created_at"].startswith("2026-11-01")
                            for item in results.json()["items"]))

    def test_semantic_memory_is_vector_indexed_and_scoped(self):
        saved = client.post("/v2/memory", json={
            "kind": "semantic",
            "content": "ULTRON preserva sua memória local mesmo ao trocar o provedor de inferência",
        }, headers=self.auth)
        self.assertEqual(saved.status_code, 200)
        self.assertTrue(saved.json()["indexed"])
        results = client.get("/v2/memory?query=memória local ULTRON", headers=self.auth)
        self.assertEqual(results.status_code, 200)
        self.assertEqual(results.json()["items"][0]["id"], saved.json()["id"])
        self.assertEqual(results.json()["items"][0]["retrieval"], "local_sparse_vector")

    def test_semantic_consolidation_keeps_explicit_source_links(self):
        source = client.post("/v2/memory", json={
            "kind": "episodic", "content": "O usuário escolheu arquitetura independente de provedor",
        }, headers=self.auth)
        self.assertEqual(source.status_code, 200)
        payload = {"candidate": "ULTRON deve manter memória independente do provedor",
                   "source_ids": [source.json()["id"]]}
        proposal = client.post("/v2/memory/curate", json=payload, headers=self.auth)
        self.assertEqual(proposal.status_code, 200)
        self.assertFalse(proposal.json()["result"]["approved"])
        committed = client.post("/v2/memory/curate/commit", json=payload, headers=self.auth)
        self.assertEqual(committed.status_code, 200)
        self.assertEqual(committed.json()["kind"], "semantic")
        with connect_db() as db:
            links = execute(db, "SELECT source_memory_id FROM cognitive_memory_links WHERE owner_id=? AND memory_id=?",
                            (self.installation_id, committed.json()["id"])).fetchall()
        self.assertEqual([int(row["source_memory_id"]) for row in links], [source.json()["id"]])

    def test_learning_gate_endpoint_blocks_per_case_regression(self):
        response = client.post("/brain/learn/evaluate", headers={"Authorization": "Bearer test-ultron-token"},
            json={"baseline": {"a": .8, "b": .8}, "candidate": {"a": .6, "b": 1.0}})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.json()["accepted"])
        self.assertEqual(response.json()["regressions"], ["a"])
        self.assertFalse(response.json()["weights_modified"])

    def test_deleting_memory_removes_its_vector(self):
        saved = client.post("/v2/memory", json={
            "kind": "semantic", "content": "registro vetorial removível do ULTRON",
        }, headers=self.auth)
        memory_id = saved.json()["id"]
        deleted = client.delete(f"/v2/memory/{memory_id}", headers=self.auth)
        self.assertEqual(deleted.status_code, 200)
        results = client.get("/v2/memory?query=registro vetorial removível", headers=self.auth)
        self.assertTrue(all(item["id"] != memory_id for item in results.json()["items"]))


if __name__ == "__main__":
    unittest.main()
