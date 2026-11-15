from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from backend import llm_provider


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.env = patch.dict(os.environ, {
            "ULTRON_LLM_BASE_URL": "https://example.ai/v1/",
            "ULTRON_LLM_API_KEY": "test-secret",
            "ULTRON_LLM_MODEL": "test-model",
        }, clear=False)
        self.env.start()
        self.addCleanup(self.env.stop)

    def test_provider_is_optional(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(llm_provider.provider_configured())
            self.assertIsNone(
                llm_provider.generate_chat_reply([{"role": "user", "content": "oi"}])
            )

    def test_generates_reply_using_compatible_endpoint(self):
        captured = {}

        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {"choices": [{"message": {"content": "Olá! Como posso ajudar?"}}]}

        def fake_post(url, **kwargs):
            captured["url"] = url
            captured["headers"] = kwargs["headers"]
            captured["json"] = kwargs["json"]
            return Response()

        with patch.object(llm_provider.httpx, "post", side_effect=fake_post):
            result = llm_provider.generate_chat_reply([
                {"role": "system", "content": "Você é ULTRON."},
                {"role": "user", "content": "Oi"},
            ])

        self.assertEqual(result, "Olá! Como posso ajudar?")
        self.assertEqual(captured["url"], "https://example.ai/v1/chat/completions")
        self.assertEqual(captured["headers"]["Authorization"], "Bearer test-secret")
        self.assertEqual(captured["json"]["model"], "test-model")
        self.assertFalse(captured["json"]["stream"])

    def test_rejects_non_https_provider(self):
        with patch.dict(os.environ, {"ULTRON_LLM_BASE_URL": "http://example.ai/v1"}):
            with self.assertRaises(llm_provider.ProviderError):
                llm_provider.generate_chat_reply([{"role": "user", "content": "oi"}])

    def test_rejects_empty_provider_reply(self):
        class Response:
            def raise_for_status(self):
                return None

            def json(self):
                return {"choices": [{"message": {"content": "  "}}]}

        with patch.object(llm_provider.httpx, "post", return_value=Response()):
            with self.assertRaises(llm_provider.ProviderError):
                llm_provider.generate_chat_reply([{"role": "user", "content": "oi"}])


if __name__ == "__main__":
    unittest.main()
