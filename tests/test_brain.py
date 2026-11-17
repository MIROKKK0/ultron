import unittest
from backend.brain import run_cognitive_cycle, run_multitask, select_research_action


class BrainTests(unittest.TestCase):
    def test_research_action_is_selected_by_neural_priority(self):
        high = select_research_action({"role_scores": {"researcher": 0.82}})
        low = select_research_action({"role_scores": {"researcher": 0.20}})
        self.assertEqual(high["action"], "web_research")
        self.assertTrue(high["allowed"])
        self.assertEqual(low["action"], "local_response")
        self.assertFalse(low["allowed"])
        self.assertEqual(high["threshold"], 0.60)

    def test_research_action_fails_closed_without_neural_priority(self):
        with self.assertRaises(RuntimeError):
            select_research_action({"role_scores": {"planner": 0.9}})

    def test_multitask_preserves_order_and_collects_results(self):
        result = run_multitask(
            ["primeira tarefa", "segunda tarefa"],
            lambda prompt: "feito: " + prompt,
        )
        self.assertEqual(result["completed"], 2)
        self.assertEqual([item["task"] for item in result["results"]], ["primeira tarefa", "segunda tarefa"])

    def test_multitask_limits_fanout(self):
        with self.assertRaises(ValueError):
            run_multitask([f"tarefa {n}" for n in range(6)], lambda prompt: prompt)

    def test_multitask_reports_partial_failure(self):
        def execute(prompt):
            if prompt == "falha":
                raise RuntimeError("provider unavailable")
            return "ok"
        result = run_multitask(["ok", "falha"], execute)
        self.assertEqual(result["completed"], 1)
        self.assertEqual(result["failed"], 1)

    def test_cognitive_cycle_adds_grounded_researcher_when_enabled(self):
        calls = []
        def execute(prompt):
            calls.append(prompt)
            return "análise com fonte"
        result = run_cognitive_cycle(
            "Pesquisar uma arquitetura", [], execute, include_researcher=True
        )
        self.assertEqual(len(result["agents"]), 4)
        self.assertIn("researcher", [item["role"] for item in result["agents"]])
        self.assertTrue(any(prompt.startswith("PESQUISA_WEB::") for prompt in calls))
        self.assertEqual(len(calls), 5)

    def test_cognitive_cycle_uses_three_roles_and_synthesis(self):
        calls = []
        def execute(prompt):
            calls.append(prompt)
            return "análise concluída"
        result = run_cognitive_cycle("Criar um plano", ["preferência: português"], execute)
        self.assertEqual(len(result["agents"]), 3)
        self.assertEqual(result["synthesis_status"], "completed")
        self.assertEqual(len(calls), 4)
        self.assertIn("núcleo neural lif é obrigatório", result["execution_policy"].lower())
        self.assertEqual(result["neural_core"]["core"], "drosophila_lif_microcircuit")
        self.assertFalse(result["neural_core"]["is_full_connectome"])


if __name__ == "__main__":
    unittest.main()
