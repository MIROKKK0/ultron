import sqlite3
import unittest

from backend.local_vector_index import LocalVectorIndex
from backend.memory_system import MemoryStore


class DeterministicEncoder:
    RETRIEVAL_KIND = "test_neural_encoder"

    def __init__(self, version, vectors):
        self.VERSION = version
        self.vectors = vectors

    def encode(self, text):
        return self.vectors.get(text, {"0": 1.0})


class LocalVectorIndexMigrationTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.store = MemoryStore(self.db)
        self.store.initialize()

    def tearDown(self):
        self.db.close()

    def test_vectors_survive_index_recreation(self):
        memory_id = self.store.add("install-a", "semantic", "The user prefers local memory", "test")
        first = LocalVectorIndex(self.db, DeterministicEncoder("test-v1", {"query": {"0": 1.0}}))
        first.initialize()
        first.upsert("install-a", memory_id, "query")

        restarted = LocalVectorIndex(self.db, DeterministicEncoder("test-v1", {"query": {"0": 1.0}}))
        restarted.initialize()
        result = restarted.search("install-a", "query")
        self.assertEqual([item["id"] for item in result], [memory_id])

    def test_encoder_version_change_reindexes_without_changing_source_memory(self):
        memory_id = self.store.add("install-a", "semantic", "A durable source fact", "test")
        first = LocalVectorIndex(self.db, DeterministicEncoder("test-v1", {"fact": {"0": 1.0}}))
        first.initialize()
        first.upsert("install-a", memory_id, "fact")

        second = LocalVectorIndex(self.db, DeterministicEncoder("test-v2", {"paraphrase": {"0": 1.0}}))
        second.initialize()
        results = second.search("install-a", "paraphrase")
        self.assertEqual([item["id"] for item in results], [memory_id])
        self.assertEqual(results[0]["encoder_version"], "test-v2")
        original = self.db.execute(
            "SELECT content,source FROM cognitive_memories WHERE owner_id=? AND id=?",
            ("install-a", memory_id),
        ).fetchone()
        self.assertEqual(original["content"], "A durable source fact")
        self.assertEqual(original["source"], "test")


if __name__ == "__main__":
    unittest.main()
