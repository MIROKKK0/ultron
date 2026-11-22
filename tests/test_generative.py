import unittest
from unittest.mock import Mock, patch

from backend.generative import generate_reply, model_config


class GenerativeModelTests(unittest.TestCase):
    @patch.dict("os.environ", {}, clear=True)
    def test_model_is_not_reported_configured_without_provider_values(self):
        self.assertFalse(model_config()["configured"])
        self.assertEqual(model_config()["provider"], "local_only")

    @patch.dict("os.environ", {
        "GEMINI_API_KEY": "legacy-secret",
    }, clear=True)
    def test_legacy_gemini_secret_does_not_activate_external_inference(self):
        config = model_config()
        self.assertFalse(config["configured"])
        self.assertEqual(config["provider"], "local_only")
        self.assertIsNone(config["api_key"])

    @patch.dict("os.environ", {
        "ULTRON_LLM_API_KEY": "test-secret",
        "ULTRON_LLM_BASE_URL": "https://provider.example/v1",
        "ULTRON_LLM_MODEL": "ultron-compatible-test",
    }, clear=True)
    @patch("backend.generative.httpx.post")
    def test_generate_reply_sends_context_and_returns_model_text(self, post):
        response = Mock()
        response.json.return_value = {
            "choices": [{"message": {"content": "Olá! Sou o ULTRON."}}]
        }
        response.raise_for_status.return_value = None
        post.return_value = response

        result = generate_reply(
            "Oi",
            history=[{"role": "user", "content": "Meu nome é teste"},
                     {"role": "assistant", "content": "Olá"}],
            memories=["Prefere respostas em português"],
        )

        self.assertEqual(result, "Olá! Sou o ULTRON.")
        kwargs = post.call_args.kwargs
        self.assertEqual(kwargs["json"]["model"], "ultron-compatible-test")
        self.assertEqual(kwargs["json"]["messages"][0]["role"], "system")
        self.assertEqual(kwargs["json"]["messages"][-1]["content"], "Oi")
        self.assertIn("Contexto recuperado", kwargs["json"]["messages"][0]["content"])
        self.assertIn("Prefere respostas em português", kwargs["json"]["messages"][0]["content"])
        self.assertEqual(kwargs["json"]["messages"][1]["content"], "Meu nome é teste")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-secret")

    @patch.dict("os.environ", {
        "ULTRON_LLM_API_KEY": "test-secret",
        "ULTRON_LLM_BASE_URL": "https://provider.example/v1",
        "ULTRON_LLM_MODEL": "ultron-compatible-test",
    }, clear=True)
    @patch("backend.generative.httpx.post")
    def test_empty_provider_response_is_rejected(self, post):
        response = Mock()
        response.json.return_value = {"choices": []}
        response.raise_for_status.return_value = None
        post.return_value = response
        with self.assertRaises(RuntimeError):
            generate_reply("Oi")

    @patch.dict("os.environ", {
        "ULTRON_LLM_API_KEY": "test-secret",
        "ULTRON_LLM_BASE_URL": "https://provider.example/v1",
        "ULTRON_LLM_MODEL": "ultron-compatible-test",
    }, clear=True)
    @patch("backend.generative.httpx.post")
    def test_programming_requests_receive_tutor_protocol(self, post):
        response = Mock()
        response.json.return_value = {"choices": [{"message": {"content": "Vamos por partes."}}]}
        response.raise_for_status.return_value = None
        post.return_value = response

        generate_reply("Me ensine Python com exercícios para iniciantes")
        system = post.call_args.kwargs["json"]["messages"][0]["content"]
        self.assertIn("MODO TUTOR DE PROGRAMAÇÃO", system)
        self.assertIn("dica antes da solução", system)
        self.assertIn("Feynman", system)

    @patch.dict("os.environ", {
        "ULTRON_LLM_API_KEY": "test-secret",
        "ULTRON_LLM_BASE_URL": "https://provider.example/v1",
        "ULTRON_LLM_MODEL": "ultron-compatible-test",
    }, clear=True)
    @patch("backend.generative.httpx.post")
    def test_regular_requests_do_not_receive_tutor_protocol(self, post):
        response = Mock()
        response.json.return_value = {"choices": [{"message": {"content": "Olá."}}]}
        response.raise_for_status.return_value = None
        post.return_value = response

        generate_reply("Qual é a capital do Brasil?")
        system = post.call_args.kwargs["json"]["messages"][0]["content"]
        self.assertNotIn("MODO TUTOR DE PROGRAMAÇÃO", system)

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_provider_configuration_fails_explicitly(self):
        with self.assertRaises(RuntimeError):
            generate_reply("Oi")


if __name__ == "__main__":
    unittest.main()
