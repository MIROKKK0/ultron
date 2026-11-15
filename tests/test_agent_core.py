import unittest

from backend.agent_core import (
    SELF_MODEL,
    improvement_proposal,
    review_response,
    system_instructions,
)


class AgentCoreTests(unittest.TestCase):
    def test_self_model_is_honest_about_limits(self):
        model = SELF_MODEL.public_dict()
        self.assertEqual(model["name"], "ULTRON")
        self.assertTrue(any("não treina pesos" in item for item in model["limitations"]))

    def test_system_instructions_include_relevant_memory(self):
        prompt = system_instructions(["Prefere respostas em português"])
        self.assertIn("Prefere respostas em português", prompt)
        self.assertIn("Não modifique o próprio código de produção", prompt)

    def test_review_is_explicitly_heuristic(self):
        result = review_response("resolver bug", "A solução é esta.")
        self.assertTrue(result["passed"])
        self.assertIn("não comprova", result["note"])

    def test_improvement_proposal_never_applies_itself(self):
        proposal = improvement_proposal("O endpoint /chat está lento")
        self.assertEqual(proposal["status"], "proposal_only")
        self.assertFalse(proposal["production_changes"])
        self.assertIn("executar testes", proposal["plan"][3])

    def test_empty_improvement_problem_is_rejected(self):
        with self.assertRaises(ValueError):
            improvement_proposal(" ")


if __name__ == "__main__":
    unittest.main()
