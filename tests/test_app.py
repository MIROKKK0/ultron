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
INSTALL_A = {"X-ULTRON-Installation-ID": "11111111-1111-4111-8111-111111111111", "X-ULTRON-Installation-Token": "a" * 64}
INSTALL_B = {"X-ULTRON-Installation-ID": "22222222-2222-4222-8222-222222222222", "X-ULTRON-Installation-Token": "b" * 64}


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

    def test_research_synthesis_always_appends_original_source_links(self):
        from backend.app import synthesize_research
        fixture = {"count": 1, "results": [{"title": "Minecraft gameplay", "snippet": "Vídeo relevante", "url": "https://www.youtube.com/watch?v=abc123", "duration": "10:20"}], "summary": "Resultados"}
        with patch("backend.app.model_config", return_value={"configured": False}):
            result = synthesize_research("vídeo Minecraft", fixture)
        self.assertIn("https://www.youtube.com/watch?v=abc123", result)
        self.assertIn("Minecraft gameplay", result)
        self.assertIn("Fontes consultadas", result)
        self.assertIn("não consegui gerar a síntese pelo Gemini", result)

    def test_natural_language_calculation_does_not_need_slash_command(self):
        response = client.post("/chat", json={"message": "Quanto é 12 vezes (3+4)?"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("84", response.json()["reply"])

    def test_bare_arithmetic_expression_is_calculated(self):
        response = client.post("/chat", json={"message": "1+9"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("10", response.json()["reply"])

    def test_unknown_message_asks_for_clarification_instead_of_echoing_request(self):
        response = client.post("/chat", json={"message": "me explica uma coisa diferente"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("reformular", response.json()["reply"])
        self.assertNotIn("Solicitação registrada", response.json()["reply"])

    def test_research_outage_does_not_return_server_error(self):
        with patch("backend.app.search_web", side_effect=RuntimeError("network down")):
            response = client.post("/chat", json={"message": "Pesquise sobre FlyWire"})
        self.assertEqual(response.status_code, 200)
        self.assertIn("pesquisa na internet", response.json()["reply"])

    def test_chat_stream_emits_processing_responding_and_final_events(self):
        response = client.post("/chat/stream", json={"message": "oi"})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.headers["content-type"].startswith("text/event-stream"))
        self.assertIn('"stage":"processing"', response.text)
        self.assertIn('"stage":"responding"', response.text)
        self.assertIn('"type":"final"', response.text)
        self.assertIn('"reply"', response.text)

    def test_runtime_status_reports_512mb_budget_and_model_limits(self):
        response = client.get("/runtime/status")
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["memory"]["budget_mb"], 512)
        self.assertFalse(payload["generative_model_configured"])
        self.assertFalse(payload["external_ai_providers"])
        self.assertIn("intent_model", payload)

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
        self.assertEqual(len(response.json()["agents"]), 4)
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
        self.assertTrue(payload["synthesis"].startswith(fixture["summary"]))
        self.assertIn("https://example.org/flywire", payload["synthesis"])
        self.assertIn("researcher", [item["role"] for item in payload["agents"]])
        self.assertIn("transformer", [item["role"] for item in payload["agents"]])
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
        self.assertEqual(len(payload["agents"]), 5)

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

    def test_memory_crud_is_installation_scoped_and_expires(self):
        for credentials in (INSTALL_A, INSTALL_B):
            registered = client.post("/installations/register", json={
                "installation_id": credentials["X-ULTRON-Installation-ID"],
                "installation_token": credentials["X-ULTRON-Installation-Token"],
            })
            self.assertEqual(registered.status_code, 200)
        headers = dict(INSTALL_A)
        created = client.post("/memory", json={"content": "Lembrar de testar o ULTRON"}, headers=headers)
        self.assertEqual(created.status_code, 200)
        memory_id = created.json()["id"]
        listed = client.get("/memory", headers=headers)
        self.assertTrue(any(item["id"] == memory_id for item in listed.json()["items"]))
        isolated = client.get("/memory", headers=INSTALL_B)
        self.assertFalse(any(item["id"] == memory_id for item in isolated.json()["items"]))
        recall = client.get("/memory/search", params={"q": "testar ULTRON"}, headers=headers)
        self.assertTrue(any(item["id"] == memory_id for item in recall.json()["items"]))
        denied_delete = client.delete(f"/memory/{memory_id}", headers={**AUTH, **INSTALL_B})
        self.assertEqual(denied_delete.status_code, 404)
        deleted = client.delete(f"/memory/{memory_id}", headers=headers)
        self.assertEqual(deleted.status_code, 200)

    def test_chat_uses_only_authenticated_installation_memory(self):
        client.post("/installations/register", json={
            "installation_id": INSTALL_A["X-ULTRON-Installation-ID"],
            "installation_token": INSTALL_A["X-ULTRON-Installation-Token"],
        })
        client.post("/memory", json={"content": "O projeto pessoal usa PostgreSQL e Python"},
                    headers=INSTALL_A)
        with patch("backend.app.model_config", return_value={"configured": True}), \
             patch("backend.app.generate_and_record", return_value="Resposta contextual") as generated:
            response = client.post("/chat", json={"message": "Explique um conceito avançado de física"},
                                   headers=INSTALL_A)
        self.assertEqual(response.status_code, 200)
        self.assertIn("PostgreSQL e Python", generated.call_args.args[2])
        with patch("backend.app.model_config", return_value={"configured": True}), \
             patch("backend.app.generate_and_record", return_value="Resposta sem memória") as generated_other:
            client.post("/chat", json={"message": "Explique um conceito avançado de física"},
                        headers=INSTALL_B)
        self.assertEqual(generated_other.call_args.args[2], [])

    def test_memory_requires_installation_scope(self):
        response = client.get("/memory", headers={})
        self.assertEqual(response.status_code, 400)

    def test_telemetry_summary_contains_aggregates_not_private_content(self):
        response = client.get("/telemetry/summary", headers=AUTH)
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertIn("latency_ms", payload)
        self.assertIn("failure_rate", payload)
        self.assertIn("input_tokens", payload)
        self.assertIn("estimated_cost_usd", payload)
        self.assertNotIn("content", payload)

    def test_public_remember_command_never_writes_shared_memory(self):
        client.post("/installations/register", json={
            "installation_id": INSTALL_A["X-ULTRON-Installation-ID"],
            "installation_token": INSTALL_A["X-ULTRON-Installation-Token"],
        })
        before = client.get("/memory", headers=INSTALL_A).json()["items"]
        response = client.post("/chat", json={"message": "/remember segredo de teste"})
        after = client.get("/memory", headers=INSTALL_A).json()["items"]
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(after), len(before))
        self.assertIn("autenticação", response.json()["reply"].lower())

    def test_native_skills_catalog_and_authenticated_runner(self):
        catalog = client.get("/skills")
        self.assertEqual(catalog.status_code, 200)
        self.assertIn("safe_evolution", {item["name"] for item in catalog.json()["skills"]})
        denied = client.post("/skills/run", json={"skill": "planner", "input": "planeje o projeto"})
        self.assertEqual(denied.status_code, 401)
        allowed = client.post("/skills/run", json={"skill": "planner", "input": "planeje o projeto"}, headers=AUTH)
        self.assertEqual(allowed.status_code, 200)
        self.assertEqual(allowed.json()["skill"], "planner")

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


    def test_natural_language_youtube_video_request_uses_video_search(self):
        fixture = {"summary": "Vídeos do YouTube encontrados", "count": 1, "results": []}
        with patch("backend.app.search_web", return_value=fixture) as search:
            response = client.post(
                "/chat",
                json={"message": "Me mostre vídeos do YouTube sobre carros do GTA V"},
            )
        self.assertEqual(response.status_code, 200)
        self.assertIn("Vídeos do YouTube", response.json()["reply"])
        search.assert_called_once_with("vídeos do YouTube sobre carros do GTA V")


if __name__ == "__main__":
    unittest.main()
