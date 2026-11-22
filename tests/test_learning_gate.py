import unittest

from backend.learning_gate import evaluate_learning_candidate


class LearningGateTests(unittest.TestCase):
    def test_accepts_candidate_without_regression(self):
        decision = evaluate_learning_candidate(
            {"cases": {"a": .8, "b": .9}},
            {"cases": {"a": .85, "b": .9}},
        )
        self.assertTrue(decision.accepted)
        self.assertEqual(decision.reason, "passed_all_frozen_cases")

    def test_rejects_regression_even_when_mean_improves(self):
        decision = evaluate_learning_candidate(
            {"cases": {"a": .6, "b": .9}},
            {"cases": {"a": .5, "b": 1.0}},
        )
        self.assertFalse(decision.accepted)
        self.assertEqual(decision.regressions, ("a",))

    def test_requires_identical_frozen_cases(self):
        with self.assertRaises(ValueError):
            evaluate_learning_candidate({"cases": {"a": .9}}, {"cases": {"b": .9}})

    def test_rejects_invalid_scores(self):
        with self.assertRaises(ValueError):
            evaluate_learning_candidate({"cases": {"a": .9}}, {"cases": {"a": 1.5}})


if __name__ == "__main__":
    unittest.main()
