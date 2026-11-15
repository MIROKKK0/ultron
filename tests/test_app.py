import os
import tempfile
import unittest
from pathlib import Path

os.environ["ULTRON_DB_PATH"] = str(Path(tempfile.gettempdir()) / "ultron-tests.sqlite3")

from fastapi.testclient import TestClient
from backend.app import app, calculate

client = TestClient(app)


class UltronTests(unittest.TestCase):
    def test_health(self):
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "ULTRON")

    def test_safe_calculation(self):
        self.assertEqual(calculate("12*(3+4)"), "84")

    def test_rejects_code_execution(self):
        with self.assertRaises(ValueError):
            calculate("__import__('os').system('echo unsafe')")

    def test_memory_crud(self):
        created = client.post("/memory", json={"content": "Lembrar de testar o ULTRON"})
        self.assertEqual(created.status_code, 200)
        memory_id = created.json()["id"]
        listed = client.get("/memory")
        self.assertTrue(any(item["id"] == memory_id for item in listed.json()["items"]))
        deleted = client.delete(f"/memory/{memory_id}")
        self.assertEqual(deleted.status_code, 200)


if __name__ == "__main__":
    unittest.main()
