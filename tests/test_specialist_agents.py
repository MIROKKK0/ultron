import unittest

from backend.specialist_agents import SPECIALISTS, run_specialist


class SpecialistAgentTests(unittest.TestCase):
    def test_registry_contains_independent_specialists(self):
        self.assertTrue({"planner", "solver", "critic", "memory_retriever",
                         "memory_curator", "evaluator"}.issubset(SPECIALISTS))

    def test_planner_returns_hierarchical_steps(self):
        result = run_specialist("planner", {"goal": "Pesquisar e depois validar fontes"})
        self.assertEqual(result["role"], "planner")
        self.assertGreaterEqual(len(result["result"]["hierarchy"]["subtasks"]), 2)

    def test_memory_curator_only_proposes_and_preserves_sources(self):
        result = run_specialist("memory_curator", {
            "candidate": "O usuário prefere português brasileiro",
            "source_ids": [3, 8],
        })["result"]
        self.assertEqual(result["status"], "proposal_only")
        self.assertFalse(result["approved"])
        self.assertEqual(result["source_ids"], [3, 8])

    def test_solver_requires_a_candidate(self):
        self.assertEqual(run_specialist("solver", {})["result"]["status"], "needs_input")

    def test_unknown_agent_is_rejected(self):
        with self.assertRaises(ValueError):
            run_specialist("root", {})


if __name__ == "__main__":
    unittest.main()
