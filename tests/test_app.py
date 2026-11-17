import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from ultron import MemoryManager, Ultron


class MemoryManagerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "memory.sqlite3"
        self.memory = MemoryManager(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_messages_are_persisted_in_chronological_order(self):
        self.memory.add_message("user", "Olá")
        self.memory.add_message("assistant", "Oi!")
        self.assertEqual(
            self.memory.get_recent_messages(),
            [
                {"role": "user", "content": "Olá"},
                {"role": "assistant", "content": "Oi!"},
            ],
        )

    def test_recent_messages_respects_limit(self):
        for index in range(4):
            self.memory.add_message("user", f"mensagem {index}")
        self.assertEqual(
            [item["content"] for item in self.memory.get_recent_messages(2)],
            ["mensagem 2", "mensagem 3"],
        )

    def test_facts_can_be_saved_updated_and_searched(self):
        self.memory.save_fact("Prefere respostas em português", "preference", 3)
        self.memory.save_fact("Prefere respostas em português", "preference", 5)
        self.memory.save_fact("Usa iPhone", "device", 2)
        self.assertEqual(
            self.memory.search_facts("português"),
            ["Prefere respostas em português"],
        )
        self.assertEqual(len(self.memory.get_all_facts()), 2)


class ToolExecutionTests(unittest.TestCase):
    def setUp(self):
        self.ultron = object.__new__(Ultron)
        self.temp_dir = tempfile.TemporaryDirectory()
        self.ultron.memory = MemoryManager(Path(self.temp_dir.name) / "memory.sqlite3")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_calculator_evaluates_basic_arithmetic(self):
        self.assertEqual(
            self.ultron._execute_tool("calculator", {"expression": "12*(3+4)"}),
            "84",
        )

    def test_calculator_rejects_code_and_non_math_characters(self):
        result = self.ultron._execute_tool(
            "calculator",
            {"expression": "__import__('os').system('echo unsafe')"},
        )
        self.assertIn("não permitidos", result)

    def test_calculator_handles_invalid_arithmetic_without_crashing(self):
        result = self.ultron._execute_tool("calculator", {"expression": "1/0"})
        self.assertIn("Erro ao executar ferramenta", result)

    def test_memory_tools_save_and_recall_facts(self):
        saved = self.ultron._execute_tool(
            "save_memory",
            {"fact": "O projeto principal é ULTRON", "category": "project", "importance": 5},
        )
        recalled = self.ultron._execute_tool(
            "recall_memory",
            {"query": "ULTRON"},
        )
        self.assertIn("salvo", saved)
        self.assertIn("O projeto principal é ULTRON", recalled)

    def test_unknown_tool_returns_a_controlled_message(self):
        self.assertEqual(
            self.ultron._execute_tool("not_a_tool", {}),
            "Ferramenta desconhecida: not_a_tool",
        )

    def test_web_search_returns_api_abstract(self):
        response = Mock()
        response.json.return_value = {"AbstractText": "Resumo de teste"}
        with patch("requests.get", return_value=response) as get:
            result = self.ultron._web_search("consulta de teste")
        self.assertEqual(result, "Resultado: Resumo de teste")
        get.assert_called_once()
        self.assertEqual(get.call_args.kwargs["timeout"], 10)

    def test_web_search_handles_network_errors(self):
        with patch("requests.get", side_effect=TimeoutError("timeout")):
            result = self.ultron._web_search("consulta de teste")
        self.assertIn("Erro na busca web", result)


if __name__ == "__main__":
    unittest.main()
