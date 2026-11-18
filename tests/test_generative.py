import unittest
from unittest.mock import Mock, patch

import httpx

from backend.generative import DEFAULT_MODEL, generate_reply, model_config


class GenerativeModelTests(unittest.TestCase):
    @patch.dict("os.environ", {}, clear=True)
    def test_model_is_not_reported_configured_without_secret(self):
        self.assertFalse(model_config()["configured"])

    @patch.dict("os.environ", {
        "GEMINI_API_KEY": "test-secret",
    }, clear=True)
    def test_gemini_defaults_are_selected(self):
        config = model_config()
        self.assertTrue(config["configured"])
        self.assertEqual(config["provider"], "gemini")
        self.assertEqual(config["model"], DEFAULT_MODEL)
        self.assertNotIn("api_key", {k: v for k, v in config.items() if k != "api_key"})

    @patch.dict("os.environ", {
        "GEMINI_API_KEY": "test-secret",
    }, clear=True)
    @patch("backend.generative.httpx.post")
    def test_generate_reply_sends_system_prompt_and_returns_model_text(self, post):
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
        self.assertEqual(kwargs["json"]["model"], DEFAULT_MODEL)
        self.assertEqual(kwargs["json"]["messages"][0]["role"], "system")
        self.assertEqual(kwargs["json"]["messages"][-1]["content"], "Oi")
        self.assertIn("Contexto recuperado", kwargs["json"]["messages"][0]["content"])
        self.assertIn("Prefere respostas em português", kwargs["json"]["messages"][0]["content"])
        self.assertEqual(kwargs["json"]["messages"][1]["content"], "Meu nome é teste")
        self.assertEqual(kwargs["headers"]["Authorization"], "Bearer test-secret")

    @patch.dict("os.environ", {"GEMINI_API_KEY": "test-secret"}, clear=True)
    @patch("backend.generative.httpx.post")
    def test_empty_provider_response_is_rejected(self, post):
        response = Mock()
        response.json.return_value = {"choices": []}
        response.raise_for_status.return_value = None
        post.return_value = response
        with self.assertRaises(RuntimeError):
            generate_reply("Oi")

    @patch.dict("os.environ", {}, clear=True)
    def test_missing_key_fails_explicitly(self):
        with self.assertRaises(RuntimeError):
            generate_reply("Oi")


if __name__ == "__main__":
    unittest.main()
