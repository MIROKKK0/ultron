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

    def test_health(self):
        response = client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["name"], "ULTRON")

    def test_safe_calculation(self):
        self.assertEqual(calculate("12*(3+4)"), "84")

    def test_rejects_code_execution(self):
        with self.assertRaises(ValueError):
            calculate("__import__('os').system('echo unsafe')")

    def test_api_requires_token(self):
        response = client.post("/chat", json={"message": "oi"})
        self.assertEqual(response.status_code, 401)

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

    def test_explicit_feedback_calibrates_only_the_selected_strategy(self):
        feedback = client.post(
            "/feedback",
            json={"rating": 5, "strategy": "solver", "comment": "A solução ajudou"},
            headers=AUTH,
        )
        self.assertEqual(feedback.status_code, 200)
        self.assertTrue(feedback.json()["used_for_policy_calibration"])
        neural_state = {
            "role_scores": {"planner": 1.0, "solver": 1.0, "critic": 1.0},
            "core": "drosophila_lif_microcircuit",
        }
        with patch("backend.app.FLY_BRAIN.process", return_value=neural_state):
            with patch("backend.app.answer_without_provider", return_value="resposta"):
                response = client.post("/chat", json={"message": "resolver tarefa"}, headers=AUTH)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["strategy"], "solver")
        self.assertGreater(neural_state["role_scores"]["solver"], 1.0)
        self.assertEqual(neural_state["policy_learning"]["synaptic_weights_changed"], False)

    def test_explicit_feedback_calibrates_only_the_selected_strategy(self):
        feedback = client.post(
            "/feedback",
            json={"rating": 5, "strategy": "solver", "comment": "A solução ajudou"},
            headers=AUTH,
        )
        self.assertEqual(feedback.status_code, 200)
        self.assertTrue(feedback.json()["used_for_policy_calibration"])
        neural_state = {
            "role_scores": {"planner": 1.0, "solver": 1.0, "critic": 1.0},
            "core": "drosophila_lif_microcircuit",
        }
        with patch("backend.app.FLY_BRAIN.process", return_value=neural_state):
            with patch("backend.app.answer_without_provider", return_value="resposta"):
                response = client.post("/chat", json={"message": "resolver tarefa"}, headers=AUTH)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["strategy"], "solver")
        self.assertGreater(neural_state["role_scores"]["solver"], 1.0)
        self.assertFalse(neural_state["policy_learning"]["synaptic_weights_changed"])

    def test_chat_includes_recent_conversation_context(self):
        save_conversation("user", "Contexto anterior de teste")
        with patch("backend.app.answer_without_provider", return_value="resposta") as mocked:
            response = client.post("/chat", json={"message": "continue"}, headers=AUTH)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(any("Contexto anterior de teste" in item for item in mocked.call_args.args[2]))

    def test_every_chat_turn_passes_through_mandatory_neural_core(self):
        neural_state = {"core": "drosophila_lif_microcircuit", "mandatory": True}
        with patch("backend.app.FLY_BRAIN.process", return_value=neural_state) as neural:
            with patch("backend.app.answer_without_provider", return_value="resposta") as provider:
                response = client.post("/chat", json={"message": "oi"}, headers=AUTH)
        self.assertEqual(response.status_code, 200)
        neural.assert_called_once()
        self.assertEqual(provider.call_args.args[3], neural_state)
        self.assertEqual(response.json()["reply"], "resposta")

    def test_chat_fails_closed_when_full_brain_is_enabled_but_unavailable(self):
        with patch("backend.app.FLY_BRAIN.process", side_effect=RuntimeError("FlyWire data unavailable")):
            response = client.post("/chat", json={"message": "quero comida"}, headers=AUTH)
        self.assertEqual(response.status_code, 503)
        self.assertIn("FlyWire data unavailable", response.json()["detail"])

    def test_brain_status(self):
        response = client.get("/brain/status", headers=AUTH)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["parallel_task_limit"], 5)

    def test_brain_run_uses_parallel_specialists(self):
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "", "OPENAI_API_KEY": ""}):
            with patch("backend.app.answer_without_provider", return_value="perspectiva"):
                response = client.post(
                    "/brain/run", json={"goal": "Planejar uma melhoria"}, headers=AUTH
                )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json()["agents"]), 3)
        self.assertEqual(response.json()["synthesis"], "perspectiva")

    def test_research_endpoint_requires_opt_in(self):
        response = client.post(
            "/brain/research", json={"goal": "Pesquisar memória de agentes"}, headers=AUTH
        )
        self.assertEqual(response.status_code, 503)

    def test_research_endpoint_is_explicitly_unavailable_without_external_services(self):
        response = client.post(
            "/brain/research", json={"goal": "Pesquisar agentes"}, headers=AUTH
        )
        self.assertEqual(response.status_code, 503)


    def test_brain_multitask(self):
        with patch.dict(os.environ, {"GOOGLE_API_KEY": "", "OPENAI_API_KEY": ""}):
            with patch("backend.app.answer_without_provider", side_effect=lambda prompt, memories=None, history=None, neural_state=None: "feito: " + prompt):
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

    def test_neural_activity_changes_local_decoding_strategy(self):
        from backend.local_decoder import decode_local
        planner = {"role_scores": {"planner": 1.0, "solver": 0.1, "critic": 0.1}}
        critic = {"role_scores": {"planner": 0.1, "solver": 0.1, "critic": 1.0}}
        a = decode_local("planeje uma melhoria complexa", neural_state=planner)
        b = decode_local("planeje uma melhoria complexa", neural_state=critic)
        self.assertIn("planner", a)
        self.assertIn("critic", b)


if __name__ == "__main__":
    unittest.main()
