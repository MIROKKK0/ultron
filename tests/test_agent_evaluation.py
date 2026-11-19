import unittest
from backend.agent_evaluation import FROZEN_PT_BR_CASES, evaluate_agent_cycle, evaluate_search_result
from backend.memory_insights import analyze_memories
from backend.specialist_agents import run_specialist

class AgentEvaluationTests(unittest.TestCase):
    def test_frozen_portuguese_cases_are_stable_and_unique(self):
        ids = [case.case_id for case in FROZEN_PT_BR_CASES]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(any(case.category == "research" for case in FROZEN_PT_BR_CASES))

    def test_search_evaluation_rejects_off_topic_result(self):
        result = evaluate_search_result("arquitetura cognitiva de agentes", {
            "results": [
                {"title": "Arquitetura de agentes inteligentes", "topic_overlap": .75, "relevance": .8},
                {"title": "ESPN fantasy basketball draft picks", "topic_overlap": 0, "relevance": .5},
            ]
        })
        self.assertEqual(result["accepted_count"], 1)
        self.assertEqual(result["rejected_count"], 1)
        self.assertEqual(result["rejected"][0]["reason"], "topic_mismatch")

    def test_memory_insights_marks_duplicates_for_review_without_merging(self):
        result = analyze_memories([
            {"id": 1, "kind": "semantic", "content": "memória local do ULTRON", "confidence": .9},
            {"id": 2, "kind": "semantic", "content": "memória local do ULTRON", "confidence": .8},
        ], {1: 0, 2: 0})
        self.assertEqual(result["duplicate_candidates"][0]["status"], "candidate_review_only")
        self.assertTrue(any("não prova" in item.lower() for item in result["analysis_limits"]))

    def test_memory_retriever_has_read_only_mode(self):
        result = run_specialist("memory_retriever", {"readonly_items": [
            {"id": 17, "kind": "semantic", "source": "benchmark", "confidence": .9}
        ]})["result"]
        self.assertTrue(result["read_only"])
        self.assertEqual(result["items"][0]["id"], 17)

    def test_cycle_evaluation_requires_planner_solver_critic_and_evidence(self):
        cycle = {
            "agents": [{"role": role, "status": "completed"} for role in ("planner", "solver", "critic")],
            "research": {"count": 0},
            "review": {"evidence_review": {"status": "reviewed"}},
        }
        self.assertTrue(evaluate_agent_cycle(cycle)["passed"])

    def test_cycle_evaluation_does_not_call_missing_critic_a_success(self):
        cycle = {"agents": [{"role": "planner", "status": "completed"}],
                 "research": None, "review": {}}
        self.assertFalse(evaluate_agent_cycle(cycle)["passed"])

if __name__ == "__main__":
    unittest.main()
