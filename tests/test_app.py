import os
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

os.environ["ULTRON_DB_PATH"] = str(Path(tempfile.gettempdir()) / "ultron-tests.sqlite3")
os.environ["ULTRON_API_TOKEN"] = "test-ultron-token"

from fastapi.testclient import TestClient
from backend.app import app, calculate, save_conversation

client = TestClient(app)
AUTH = {"Authorization": "Bearer test-ultron-token"}


class UltronTests(unittest.TestCase):
    def test_root_and_local_self_command(self):
        root = client.get("/")
        self.assertEqual(root.status_code, 200)
        self.assertEqual(root.json()["name"], "ULTRON")
        response = client.post("/chat", json={"message": "/self"}, headers=AUTH)
        self.assertEqual(response.status_code, 200)
        self.assertIn("ULTRON", response.json()["reply"])

    def test_root_post_is_a_normal_chat_alias(self):
        response = client.post("/", json={"message": "oi"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("ULTRON", response.json()["reply"])

    def test_natural_language_research_does_not_need_slash_command(self):
        fixture = {"summary": "Fontes atuais: https://example.org"}
        with patch("backend.app.search_web", return_value=fixture) as search:
            response = client.post("/chat", json={"message": "Pesquise na internet sobre FlyWire"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("https://example.org", response.json()["reply"])
        search.assert_called_once_with("FlyWire")

    def test_natural_language_calculation_does_not_need_slash_command(self):
        response = client.post("/chat", json={"message": "Quanto é 12 vezes (3+4)?"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("84", response.json()["reply"])

    def test_research_outage_does_not_return_server_error(self):
        with patch("backend.app.search_web", side_effect=RuntimeError("network down")):
            response = client.post("/chat", json={"message": "Pesquise sobre FlyWire"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("pesquisa na internet", response.json()["reply"])

    def test_health(self):
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "ULTRON")

    def test_safe_calculation(self):
        self.assertEqual(calculate("12*(3+4)"), "84")

    def test_rejects_code_execution(self):
        with self.assertRaises(ValueError):
            calculate("__import__('os').system('echo unsafe')")

    def test_chat_is_available_without_manual_server_token(self):
        response = client.post("/chat", json={"message": "oi"})
        self.assertEqual(response.status_code, 200)

    def test_agent_self_and_planner(self):
        identity = client.get("/self", headers=AUTH)
        self.assertEqual(identity.status_code, 200)
        self.assertEqual(identity.json()["identity"]["name"], "ULTRON")
        plan = client.post("/agent/plan", json={"goal": "Apagar dados antigos"}, headers=AUTH)
        self.assertEqual(plan.status_code, 200)
        self.assertTrue(plan.json()["human_approval_required"])

    def test_feedback_is_persisted(self):
        response = client.post("/feedback", json={"rating": 5, "comment": "Resposta útil"}, headers=AUTH)
        self.assertEqual(response.status_code, 200)
        summary = client.get("/feedback/summary", headers=AUTH)
        self.assertGreaterEqual(summary.json()["total"], 1)

    def test_public_feedback_is_stored_and_calibrates_only_bounded_strategy_priority(self):
        feedback = client.post(
            "/feedback",
            json={"rating": 5, "strategy": "solver", "comment": "A solução ajudou"},
            headers=AUTH,
        )
        self.assertEqual(feedback.status_code, 200)
        self.assertTrue(feedback.json()["stored"])
        self.assertTrue(feedback.json()["used_for_policy_calibration"])
        self.assertEqual(feedback.json()["learning_scope"], "bounded_strategy_priority_only")

    def test_public_chat_does_not_read_shared_private_conversation_context(self):
        save_conversation("user", "Contexto privado de teste")
        with patch("backend.app.answer_without_provider", return_value="resposta") as mocked:
            response = client.post("/chat", json={"message": "continue"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(mocked.call_args.args[1], [])
        self.assertEqual(mocked.call_args.args[2], [])

    def test_chat_returns_only_a_feedback_supported_strategy(self):
        with patch("backend.app.answer_without_provider", return_value="resposta"):
            response = client.post("/chat", json={"message": "oi"}, headers=AUTH)
        self.assertEqual(response.status_code, 200)
        self.assertIn(response.json()["strategy"], {"planner", "solver", "critic"})

    def test_reward_learning_and_recall_endpoints_are_protected_and_functional(self):
        learned = client.post(
            "/brain/learn",
            json={"context": "gostei de respostas úteis", "outcome": "resposta útil", "reward": 1.0},
            headers=AUTH,
        )
        self.assertEqual(learned.status_code, 200)
        self.assertEqual(learned.json()["method"], "three_factor_reward_modulated_association")
        recalled = client.post(
            "/brain/recall", json={"context": "gostei de respostas úteis"}, headers=AUTH
        )
        self.assertEqual(recalled.status_code, 200)
        self.assertTrue(recalled.json()["associations"])

    def test_reward_learning_rejects_missing_authentication(self):
        response = client.post(
            "/brain/learn",
            json={"context": "entrada", "outcome": "saída", "reward": 1.0},
        )
        self.assertEqual(response.status_code, 401)

    def test_brain_status(self):
        response = client.get("/brain/status", headers=AUTH)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["parallel_task_limit"], 5)
        self.assertFalse(response.json()["neural_core_configured"])

    def test_brain_run_uses_parallel_specialists(self):
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "", "OPENAI_API_KEY": ""}):
            with patch("backend.app.answer_without_provider", return_value="perspectiva"):
                response = client.post(
                    "/brain/run", json={"goal": "Planejar uma melhoria"}, headers=AUTH
                )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["agents"]), 3)
        self.assertEqual(response.json()["synthesis"], "perspectiva")


    def test_public_brain_command_runs_cognitive_cycle_without_private_memories(self):
        expected = {"synthesis": "Plano processado pelo ciclo cognitivo"}
        with patch("backend.app.execute_brain_cycle", return_value=expected) as cycle:
            response = client.post("/chat", json={"message": "/brain planejar uma melhoria"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["reply"], expected["synthesis"])
        self.assertEqual(cycle.call_args.args[0], "planejar uma melhoria")
        self.assertFalse(cycle.call_args.kwargs["include_private_memories"])
        self.assertNotIn("neural_state", cycle.call_args.kwargs)

    def test_public_brain_command_rejects_empty_goal(self):
        response = client.post("/chat", json={"message": "/brain "})
        self.assertEqual(response.status_code, 200)
        self.assertIn("Informe o objetivo", response.json()["reply"])

    def test_brain_run_executes_real_specialists_and_web_research(self):
        fixture = {
            "query": "FlyWire connectome",
            "count": 1,
            "results": [{"title": "FlyWire paper", "url": "https://example.org/flywire", "snippet": "Connectome data"}],
            "summary": "Fontes verificáveis sobre FlyWire: https://example.org/flywire",
        }
        with patch("backend.app.answer_without_provider", return_value="Resposta local"):
            with patch("backend.app.search_web", return_value=fixture) as search:
                response = client.post(
                    "/brain/run",
                    json={"goal": "Pesquise na internet sobre FlyWire connectome"},
                    headers=AUTH,
                )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["brain_version"], "4.0.0-local-tools")
        self.assertEqual(payload["plan"]["goal"], "Pesquise na internet sobre FlyWire connectome")
        self.assertEqual(payload["review"]["checks"]["has_answer"], True)
        self.assertEqual(payload["synthesis"], fixture["summary"])
        self.assertIn("researcher", [item["role"] for item in payload["agents"]])
        researcher = next(item for item in payload["agents"] if item["role"] == "researcher")
        self.assertEqual(researcher["status"], "completed")
        search.assert_called_once_with("FlyWire connectome")

    def test_brain_run_keeps_other_specialists_when_web_search_fails(self):
        with patch("backend.app.answer_without_provider", return_value="Resposta local"):
            with patch("backend.app.search_web", side_effect=RuntimeError("network down")):
                response = client.post(
                    "/brain/run",
                    json={"goal": "Pesquise na internet sobre FlyWire"},
                    headers=AUTH,
                )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["synthesis"], "Resposta local")
        self.assertEqual(next(item for item in payload["agents"] if item["role"] == "researcher")["status"], "failed")
        self.assertEqual(len(payload["agents"]), 4)

    def test_research_endpoint_returns_source_linked_results(self):
        fixture = {"query": "memória de agentes", "count": 1, "results": [{"title": "Paper", "url": "https://example.org/paper", "snippet": "Resumo"}], "summary": "Fontes"}
        with patch("backend.app.search_web", return_value=fixture):
            response = client.post("/brain/research", json={"goal": "Pesquisar memória de agentes"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"][0]["url"], "https://example.org/paper")

    def test_chat_research_command_uses_web_search(self):
        fixture = {"summary": "Resultados com fontes: https://example.org"}
        with patch("backend.app.search_web", return_value=fixture):
            response = client.post("/chat", json={"message": "/research FlyWire connectome"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("https://example.org", response.json()["reply"])


    def test_brain_multitask(self):
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "", "OPENAI_API_KEY": ""}):
            with patch("backend.app.answer_without_provider", side_effect=lambda prompt, memories=None, history=None: "feito: " + prompt):
                response = client.post(
                    "/brain/multitask",
                    json={"tasks": ["resumir projeto", "listar riscos"]},
                    headers=AUTH,
                )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["completed"], 2)

    def test_memory_crud(self):
        created = client.post(
            "/memory",
            json={"content": "Lembrar de testar o ULTRON"},
            headers=AUTH,
        )
        self.assertEqual(created.status_code, 200)
        memory_id = created.json()["id"]
        listed = client.get("/memory", headers=AUTH)
        self.assertTrue(any(item["id"] == memory_id for item in listed.json()["items"]))
        deleted = client.delete(f"/memory/{memory_id}", headers=AUTH)
        self.assertEqual(deleted.status_code, 200)

    def test_normal_chat_works_without_any_ai_provider_token(self):
        response = client.post("/chat", json={"message": "oi"}, headers=AUTH)
        self.assertEqual(response.status_code, 200)
        self.assertIn("ULTRON", response.json()["reply"])

    def test_local_decoder_does_not_depend_on_neural_state(self):
        from backend.local_decoder import decode_local
        self.assertEqual(
            decode_local("planeje uma melhoria complexa"),
            decode_local("planeje uma melhoria complexa"),
        )


if __name__ == "__main__":
    unittest.main()
