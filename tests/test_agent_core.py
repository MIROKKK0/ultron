import unittest
import sqlite3

from backend.agent_core import (
    SELF_MODEL,
    improvement_proposal,
    review_response,
    system_instructions,
    rank_memories,
    plan_task,
)


class AgentCoreTests(unittest.TestCase):
    def test_self_model_is_honest_about_limits(self):
        model = SELF_MODEL.public_dict()
        self.assertEqual(model["name"], "ULTRON")
        self.assertTrue(any("não treina pesos" in item for item in model["limitations"]))

    def test_system_instructions_include_relevant_memory(self):
        prompt = system_instructions(["Prefere respostas em português"])
        self.assertIn("Prefere respostas em português", prompt)
        self.assertIn("Nunca modifique o próprio código de produção", prompt)

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

    def test_memory_ranking_prefers_relevant_content(self):
        memories = [
            {"content": "Projeto ULTRON usa Gemini"},
            {"content": "Receita de bolo de cenoura"},
        ]
        self.assertEqual(rank_memories("configurar Gemini no ULTRON", memories)[0], "Projeto ULTRON usa Gemini")

    def test_memory_ranking_accepts_sqlite_rows(self):
        connection = sqlite3.connect(":memory:")
        connection.row_factory = sqlite3.Row
        connection.execute("CREATE TABLE memories(content TEXT)")
        connection.execute("INSERT INTO memories(content) VALUES (?)", ("ULTRON usa Gemini",))
        rows = connection.execute("SELECT content FROM memories").fetchall()
        self.assertEqual(rank_memories("configurar Gemini", rows)[0], "ULTRON usa Gemini")
        connection.close()

    def test_planner_marks_destructive_actions_for_approval(self):
        plan = plan_task("Apagar todos os dados antigos")
        self.assertEqual(plan["risk"], "high")
        self.assertTrue(plan["human_approval_required"])


if __name__ == "__main__":
    unittest.main()
