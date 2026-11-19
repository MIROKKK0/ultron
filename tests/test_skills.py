import unittest

from backend.skills import list_skills, run_intent_skill, run_named_skill

class SkillTests(unittest.TestCase):
    def test_skill_catalog_is_present(self):
        names = {item["name"] for item in list_skills()}
        self.assertTrue({"conversation", "planner", "self_review", "safe_evolution", "memory"} <= names)

    def test_planner_skill_runs(self):
        response = run_intent_skill("planeje meu projeto em etapas")
        self.assertIn("Plano para:", response)

    def test_safe_evolution_is_proposal_only(self):
        result = run_named_skill("safe_evolution", "melhore sua arquitetura")
        self.assertIn("branch/PR", result["response"])
        self.assertEqual(result["model"]["intent"], "improve")

    def test_public_memory_skill_does_not_write_shared_memory(self):
        response = run_intent_skill("guarde essa informação")
        self.assertIn("não grava memórias compartilhadas", response)

if __name__ == "__main__":
    unittest.main()
