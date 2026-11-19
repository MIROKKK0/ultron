import unittest

try:
    import torch
except ImportError:
    torch = None


@unittest.skipIf(torch is None, "PyTorch is installed only in the optional neural workflow")
class SemanticEncoderBenchmarkTests(unittest.TestCase):
    def test_candidate_with_any_case_regression_is_not_clean(self):
        from training.generative.train_semantic_encoder import compare_case_ranks
        result = compare_case_ranks([1, 2, 3, 4], [1, 4, 2, 4])
        self.assertEqual(result, {"cases": 4, "regressions": 1, "improvements": 1, "unchanged": 2})

    def test_rejects_empty_or_mismatched_rank_lists(self):
        from training.generative.train_semantic_encoder import compare_case_ranks
        with self.assertRaises(ValueError):
            compare_case_ranks([], [])
        with self.assertRaises(ValueError):
            compare_case_ranks([1, 2], [1])


if __name__ == "__main__":
    unittest.main()
