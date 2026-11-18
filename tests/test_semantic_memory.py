import json
import unittest

from backend.semantic_memory import cosine_similarity, rank_semantic


class SemanticMemoryTests(unittest.TestCase):
    def test_cosine_similarity_is_one_for_same_vector(self):
        self.assertAlmostEqual(cosine_similarity([1.0, 0.0], [1.0, 0.0]), 1.0)

    def test_cosine_similarity_handles_zero_and_dimension_mismatch(self):
        self.assertEqual(cosine_similarity([0.0, 0.0], [1.0, 1.0]), 0.0)
        self.assertEqual(cosine_similarity([1.0], [1.0, 0.0]), 0.0)

    def test_semantic_ranker_orders_by_similarity(self):
        rows = [
            {"id": 1, "content": "less similar", "created_at": "2026-01-01",
             "expires_at": None, "embedding_json": json.dumps([0.0, 1.0])},
            {"id": 2, "content": "best match", "created_at": "2026-01-02",
             "expires_at": None, "embedding_json": json.dumps([1.0, 0.0])},
        ]
        ranked = rank_semantic([1.0, 0.0], rows)
        self.assertEqual(ranked[0]["id"], 2)
        self.assertGreater(ranked[0]["relevance"], ranked[1]["relevance"])

    def test_semantic_ranker_skips_corrupt_embeddings(self):
        rows = [{"id": 1, "content": "bad", "created_at": "", "expires_at": None,
                 "embedding_json": "not-json"}]
        self.assertEqual(rank_semantic([1.0, 0.0], rows), [])


if __name__ == "__main__":
    unittest.main()
