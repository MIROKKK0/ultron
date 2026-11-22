import unittest

from scripts.agent_eval import run


class AgentEvaluationMetricsTests(unittest.TestCase):
    def test_recursive_worker_is_an_additive_metric(self):
        report = run()
        self.assertIn("recursive_code_evolution_worker", report["metrics"])
        self.assertTrue(report["passed"])
        self.assertGreaterEqual(report["score"], 0.0)
        self.assertLessEqual(report["score"], 1.0)


if __name__ == "__main__":
    unittest.main()
