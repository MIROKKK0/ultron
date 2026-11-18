import unittest

from ultron_core.governance import evaluate_evolution
from ultron_core.orchestrator import EvolutionOrchestrator, TestResult
from pathlib import Path


class GovernanceTests(unittest.TestCase):
    def test_green_tests_allow_reviewable_change_not_direct_publish(self):
        decision = evaluate_evolution(["src/example.py"], tests_passed=True, diff_valid=True)
        self.assertTrue(decision.accepted)
        self.assertFalse(decision.publishable)

    def test_failed_tests_block_change(self):
        decision = evaluate_evolution(["src/example.py"], tests_passed=False, diff_valid=True)
        self.assertFalse(decision.accepted)
        self.assertIn("tests_not_passed", decision.reasons)

    def test_sensitive_paths_require_human_review(self):
        decision = evaluate_evolution([".env"], tests_passed=True, diff_valid=True)
        self.assertFalse(decision.accepted)
        self.assertIn("human_review_required", decision.reasons)

    def test_sensitive_path_can_be_reviewed_but_never_auto_published(self):
        decision = evaluate_evolution(["src/auth.py"], tests_passed=True, diff_valid=True, human_review=True)
        self.assertTrue(decision.accepted)
        self.assertFalse(decision.publishable)

    def test_budget_and_invalid_patch_block(self):
        decision = evaluate_evolution(["src/a.py"], tests_passed=True, diff_valid=False, within_budget=False)
        self.assertFalse(decision.accepted)
        self.assertIn("invalid_patch", decision.reasons)
        self.assertIn("execution_budget_exceeded", decision.reasons)


class OrchestratorTests(unittest.TestCase):
    def test_path_escape_is_rejected(self):
        runner = EvolutionOrchestrator(Path.cwd())
        self.assertFalse(runner.validate_patch_paths(["../../outside.txt"]))
        self.assertTrue(runner.validate_patch_paths(["src/module.py"]))

    def test_test_failure_blocks_decision(self):
        runner = EvolutionOrchestrator(Path.cwd())
        decision = runner.decide(["src/module.py"], TestResult(False, 1, "failed"), diff_valid=True)
        self.assertFalse(decision.accepted)


if __name__ == "__main__":
    unittest.main()
