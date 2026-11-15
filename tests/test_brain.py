import unittest
from backend.brain import run_cognitive_cycle, run_multitask


class BrainTests(unittest.TestCase):
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

    def test_cognitive_cycle_uses_three_roles_and_synthesis(self):
        calls = []
        def execute(prompt):
            calls.append(prompt)
            return "análise concluída"
        result = run_cognitive_cycle("Criar um plano", ["preferência: português"], execute)
        self.assertEqual(len(result["agents"]), 3)
        self.assertEqual(result["synthesis_status"], "completed")
        self.assertEqual(len(calls), 4)
        self.assertIn("nenhuma ação externa", result["execution_policy"].lower())


if __name__ == "__main__":
    unittest.main()
