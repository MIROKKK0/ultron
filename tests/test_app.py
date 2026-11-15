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

    def test_public_chat_does_not_persist_shared_conversations(self):
        with patch("backend.app.save_conversation") as save:
            response = client.post("/chat", json={"message": "conversa privada"})
        self.assertEqual(response.status_code, 200)
        save.assert_not_called()

    def test_public_remember_request_does_not_write_shared_memory(self):
        with patch("backend.app.connect_db") as connect:
            response = client.post("/chat", json={"message": "lembre que gosto de respostas curtas"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("identificação segura por instalação", response.json()["reply"])
        connect.assert_not_called()

    def test_every_chat_turn_passes_through_mandatory_neural_core(self):
        neural_state = {"core": "drosophila_lif_microcircuit", "mandatory": True}
        with patch("backend.app.FLY_BRAIN.process", return_value=neural_state) as neural:
            with patch("backend.app.answer_without_provider", return_value="resposta") as provider:
                response = client.post("/chat", json={"message": "oi"}, headers=AUTH)
        self.assertEqual(response.status_code, 200)
        neural.assert_called_once()
        self.assertEqual(provider.call_args.args[3], neural_state)
        self.assertEqual(response.json()["reply"], "resposta")
        self.assertEqual(response.json()["brain_context"]["core"], "drosophila_lif_microcircuit")
        self.assertEqual(response.json()["brain_context"]["is_full_connectome"], False)
        self.assertEqual(response.json()["brain_context"]["neurons"], 48)
        self.assertEqual(response.json()["brain_context"]["simulation_steps"], 40)
        self.assertEqual(response.json()["brain_context"]["role_scores"], {"planner": 0.0, "solver": 0.0, "critic": 0.0})

    def test_chat_fails_closed_when_full_brain_is_enabled_but_unavailable(self):
        with patch("backend.app.FLY_BRAIN.process", side_effect=RuntimeError("FlyWire data unavailable")):
            response = client.post("/chat", json={"message": "quero comida"}, headers=AUTH)
        self.assertEqual(response.status_code, 503)
        self.assertIn("FlyWire data unavailable", response.json()["detail"])

    def test_chat_returns_only_a_feedback_supported_strategy(self):
        neural_state = {
            "role_scores": {"planner": 1.0, "solver": 1.0, "critic": 1.0, "researcher": 99.0},
        }
        with patch("backend.app.FLY_BRAIN.process", return_value=neural_state):
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
        self.assertFalse(learned.json()["flywire_synapses_modified"])
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

    def test_brain_status_reports_real_readiness_without_host_paths(self):
        with patch("backend.app.flywire_status", return_value={
            "available": False,
            "connectome": "FlyWire FAFB v783",
            "expected_neurons": 138639,
            "upstream_code_present": False,
            "missing_files": ["data/2025_Completeness_783.csv"],
            "missing_code_files": ["code/run_pytorch.py"],
            "missing_dependencies": ["torch"],
            "backend": "PyTorch CPU",
            "root": "/private/host/path",
        }):
            with patch("backend.app.flywire_runtime_loaded", return_value=False):
                response = client.get("/brain/status", headers=AUTH)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["parallel_task_limit"], 5)
        self.assertEqual(payload["neural_core"]["microcircuit_neurons"], 48)
        self.assertEqual(payload["neural_core"]["full_connectome"]["expected_neurons"], 138639)
        self.assertEqual(payload["neural_core"]["full_connectome"]["snapshot_neurons"], 139255)
        self.assertEqual(payload["neural_core"]["full_connectome"]["unmodeled_snapshot_neurons"], 616)
        self.assertEqual(payload["neural_core"]["full_connectome"]["model_coverage_percent"], 99.56)
        self.assertEqual(payload["neural_core"]["full_connectome"]["missing_dependencies"], ["torch"])
        self.assertNotIn("/private/host/path", response.text)
        self.assertFalse(payload["neural_core"]["full_connectome_loaded"])
        self.assertFalse(payload["neural_core"]["full_connectome_ready"])
        self.assertFalse(payload["neural_core"]["full_connectome"]["memory_budget"]["ready"])
        self.assertFalse(payload["learning"]["modifies_flywire_synapses"])
        self.assertFalse(payload["memory_enabled"])
        self.assertTrue(payload["memory_api_requires_bearer_auth"])
        self.assertFalse(payload["public_chat_memory_enabled"])

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
        self.assertIn("neural_state", cycle.call_args.kwargs)

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
            with patch("backend.app.answer_without_provider", side_effect=lambda prompt, memories=None, history=None, neural_state=None: "feito: " + prompt):
                response = client.post(
                    "/brain/multitask",
                    json={"tasks": ["resumir projeto", "listar riscos"]},
                    headers=AUTH,
                )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["completed"], 2)

    def test_private_memory_endpoints_reject_missing_authentication(self):
        created = client.post("/memory", json={"content": "não deve ser público"})
        self.assertEqual(created.status_code, 401)
        listed = client.get("/memory")
        self.assertEqual(listed.status_code, 401)
        deleted = client.delete("/memory/1")
        self.assertEqual(deleted.status_code, 401)

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
