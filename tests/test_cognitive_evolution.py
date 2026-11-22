import sqlite3
import unittest
from backend.evidence_critic import review_evidence
from backend.memory_system import MemoryStore
from backend.hierarchical_planner import plan_hierarchical
from backend.tool_runtime import ToolRegistry, ToolSpec
from backend.improvement_cycle import Evaluation, compare_candidate

class CognitiveEvolutionTests(unittest.TestCase):
    def test_critic_flags_claims_without_evidence_and_unmatched_links(self):
        result = review_evidence("pesquisa", "A conclusão é definitiva. https://unknown.example")
        self.assertTrue(result["needs_human_or_source_check"])
        self.assertEqual(len(result["unsupported_answer_urls"]), 1)

    def test_critic_accepts_matching_source_as_evidence_pointer_not_truth(self):
        evidence = [{"url": "https://example.org", "title": "Estudo", "snippet": "resultado"}]
        result = review_evidence("pesquisa", "Veja https://example.org", evidence)
        self.assertEqual(result["unsupported_answer_urls"], [])
        self.assertIn("não comprova", " ".join(result["limitations"]))

    def test_memory_types_are_scoped_and_deletable(self):
        db = sqlite3.connect(":memory:")
        db.row_factory = sqlite3.Row
        store = MemoryStore(db)
        store.initialize()
        mid = store.add("install-A", "episodic", "Teste de recuperação", "conversation")
        store.add("install-B", "semantic", "Teste de recuperação", "verified-note")
        self.assertEqual(len(store.retrieve("install-A", "recuperação")), 1)
        self.assertEqual(store.retrieve("install-A", "recuperação")[0]["kind"], "episodic")
        self.assertTrue(store.forget("install-A", mid))
        self.assertEqual(store.retrieve("install-A", "recuperação"), [])

    def test_hierarchical_plan_has_dependencies_and_failure_scenarios(self):
        plan = plan_hierarchical("Pesquisar fontes e depois comparar resultados")
        self.assertEqual(len(plan["subtasks"]), 2)
        self.assertEqual(plan["dependencies"][0]["after"], "T2")
        self.assertEqual(len(plan["simulated_outcomes"]), 3)

    def test_tool_runtime_observes_and_recovers_idempotent_failure(self):
        calls = {"n": 0}
        def flaky():
            calls["n"] += 1
            if calls["n"] == 1: raise TimeoutError()
            return "ok"
        registry = ToolRegistry()
        registry.register(ToolSpec("safe_read", flaky, True, 1))
        result = registry.execute("safe_read")
        self.assertEqual(result["status"], "completed")
        self.assertTrue(result["recovered"])
        self.assertEqual(result["attempts"], 2)

    def test_tool_runtime_never_retries_non_idempotent_actions(self):
        calls = {"n": 0}
        def flaky():
            calls["n"] += 1
            raise TimeoutError()
        registry = ToolRegistry()
        registry.register(ToolSpec("send", flaky, False, 2))
        result = registry.execute("send")
        self.assertEqual(result["attempts"], 1)
        self.assertEqual(calls["n"], 1)

    def test_promotion_requires_gain_and_zero_regressions(self):
        base = Evaluation(.80, 0, 0, 100)
        good = compare_candidate(base, Evaluation(.83, 0, 0, 110))
        bad = compare_candidate(base, Evaluation(.90, 1, 0, 110))
        self.assertEqual(good["promotion"], "eligible_for_pr")
        self.assertEqual(bad["promotion"], "rejected")

if __name__ == "__main__":
    unittest.main()
