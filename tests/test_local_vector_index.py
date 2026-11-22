import unittest
import sqlite3

from backend.local_vector_index import LocalSparseVectorizer, LocalVectorIndex, cosine


class LocalVectorIndexTests(unittest.TestCase):
    def setUp(self):
        self.db = sqlite3.connect(":memory:")
        self.db.row_factory = sqlite3.Row
        self.db.executescript("""
            CREATE TABLE cognitive_memories (
                id INTEGER PRIMARY KEY, owner_id TEXT, kind TEXT, content TEXT, source TEXT,
                confidence REAL, created_at TEXT, last_accessed_at TEXT, access_count INTEGER
            );
        """)
        self.index = LocalVectorIndex(self.db)
        self.index.initialize()
        for memory_id, owner, kind, content in [
            (1, "device-a", "semantic", "ULTRON preserva memória local persistente"),
            (2, "device-a", "episodic", "Hoje configurei o aplicativo no iPhone"),
            (3, "device-b", "semantic", "ULTRON memória local independente"),
        ]:
            self.db.execute("""INSERT INTO cognitive_memories
                VALUES(?,?,?,?,?,?,?,?,0)""",
                (memory_id, owner, kind, content, "test", .9, "now", "now"))

    def tearDown(self):
        self.db.close()

    def test_vectorizer_is_deterministic_and_normalized(self):
        encoder = LocalSparseVectorizer()
        a = encoder.encode("memória persistente ULTRON")
        self.assertEqual(a, encoder.encode("memória persistente ULTRON"))
        self.assertAlmostEqual(sum(v*v for v in a.values()), 1.0, places=5)

    def test_vector_search_ranks_related_text_and_isolates_owner(self):
        self.index.upsert("device-a", 1, "ULTRON preserva memória local persistente")
        self.index.upsert("device-a", 2, "Hoje configurei o aplicativo no iPhone")
        self.index.upsert("device-b", 3, "ULTRON memória local independente")
        results = self.index.search("device-a", "memória persistente ULTRON")
        self.assertEqual(results[0]["id"], 1)
        self.assertTrue(all(item["id"] != 3 for item in results))

    def test_kind_filter_and_delete(self):
        self.index.upsert("device-a", 1, "ULTRON preserva memória local persistente")
        self.index.upsert("device-a", 2, "Hoje configurei o aplicativo no iPhone")
        self.assertTrue(all(item["kind"] == "semantic" for item in
                            self.index.search("device-a", "memória ULTRON", kind="semantic")))
        self.index.delete("device-a", 1)
        self.assertEqual(self.index.search("device-a", "memória ULTRON"), [])

    def test_cosine_handles_empty_vectors(self):
        self.assertEqual(cosine({}, {"1": 1.0}), 0.0)


if __name__ == "__main__":
    unittest.main()
