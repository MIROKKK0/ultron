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


class MemoryInsightsApiTests(unittest.TestCase):
    def setUp(self):
        self.installation_id = "insights-" + uuid.uuid4().hex
        self.token = uuid.uuid4().hex + uuid.uuid4().hex
        digest = hashlib.sha256(self.token.encode("utf-8")).hexdigest()
        with connect_db() as db:
            execute(db, "INSERT INTO installations(installation_id,token_hash,created_at,revoked_at) VALUES(?,?,?,NULL)",
                    (self.installation_id, digest, "2026-11-19T00:00:00+00:00"))
        self.headers = {
            "X-Installation-ID": self.installation_id,
            "X-Installation-Token": self.token,
        }

    def test_insights_are_private_read_only_and_route_six_specialists(self):
        first = client.post("/v2/memory", headers=self.headers, json={
            "kind": "semantic", "content": "ULTRON mantém memória local independente",
        })
        second = client.post("/v2/memory", headers=self.headers, json={
            "kind": "semantic", "content": "ULTRON mantém memória local independente",
        })
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 200)

        before = client.get("/v2/memory", headers=self.headers).json()["items"]
        response = client.get("/v2/memory/insights", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload["read_only"])
        self.assertEqual(payload["writes_performed"], 0)
        self.assertGreaterEqual(len(payload["duplicate_candidates"]), 1)
        self.assertEqual(
            {item["role"] for item in payload["specialist_cycle"]},
            {"planner", "memory_retriever", "solver", "critic", "memory_curator", "evaluator"},
        )
        after = client.get("/v2/memory", headers=self.headers).json()["items"]
        self.assertEqual(
            [(item["id"], item["access_count"], item["last_accessed_at"]) for item in before],
            [(item["id"], item["access_count"], item["last_accessed_at"]) for item in after],
        )

    def test_insights_require_installation_authentication(self):
        response = client.get("/v2/memory/insights")
        self.assertEqual(response.status_code, 401)


if __name__ == "__main__":
    unittest.main()
