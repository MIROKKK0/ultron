import unittest

from backend.memory_insights import analyze_memories


class MemoryInsightsTests(unittest.TestCase):
    def test_detects_repeated_content_without_merging(self):
        items = [
            {"id": 1, "kind": "semantic", "content": "ULTRON mantém memória local independente", "confidence": 0.9},
            {"id": 2, "kind": "semantic", "content": "ULTRON mantém memória local independente", "confidence": 0.8},
        ]
        result = analyze_memories(items, {1: 0, 2: 0})
        self.assertEqual(result["duplicate_candidates"][0]["memory_ids"], [1, 2])
        self.assertEqual(result["duplicate_candidates"][0]["status"], "candidate_review_only")
        self.assertIn("episodic", result["counts_by_kind"])
        self.assertTrue(any(gap["type"] == "missing_memory_kind" for gap in result["knowledge_gaps"]))

    def test_empty_memories_return_explicit_gaps(self):
        result = analyze_memories([], {})
        self.assertEqual(result["duplicate_candidates"], [])
        self.assertEqual(result["counts_by_kind"], {"episodic": 0, "semantic": 0, "procedural": 0})
        self.assertEqual(len(result["knowledge_gaps"]), 3)

    def test_low_confidence_is_reported_not_promoted(self):
        result = analyze_memories([
            {"id": 9, "kind": "episodic", "content": "Registro isolado", "confidence": 0.2},
        ], {9: 0})
        self.assertEqual(result["low_confidence_memories"][0]["memory_id"], 9)
        self.assertEqual(result["low_confidence_memories"][0]["confidence"], 0.2)


if ( __name__ == "__main__"):
    unittest.main()
