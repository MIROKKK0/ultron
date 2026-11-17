import os
import unittest
from unittest.mock import patch

from backend.hosted_language import configured_providers, generate_reply


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self.payload = payload

    def json(self):
        return self.payload


class FakeClient:
    def __init__(self, response, calls):
        self.response = response
        self.calls = calls

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def post(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


class HostedLanguageTests(unittest.TestCase):
    def test_no_keys_keeps_local_path(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(configured_providers(), [])
            self.assertIsNone(generate_reply("oi", {}))

    def test_provider_order_only_returns_configured_known_providers(self):
        env = {
            "GEMINI_API_KEY": "gemini-secret",
            "GROQ_API_KEY": "groq-secret",
            "OPENROUTER_API_KEY": "",
            "ULTRON_AI_PROVIDER_ORDER": "groq,unknown,gemini,groq",
        }
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(configured_providers(), ["groq", "gemini"])

    def test_primary_rate_limit_falls_back_to_next_free_provider(self):
        calls = []
        responses = [
            FakeResponse(429, {"error": "rate limited"}),
            FakeResponse(200, {"choices": [{"message": {"content": "Resposta online"}}]}),
        ]
        clients = [FakeClient(response, calls) for response in responses]
        env = {
            "GEMINI_API_KEY": "gemini-secret",
            "GROQ_API_KEY": "groq-secret",
            "ULTRON_AI_PROVIDER_ORDER": "gemini,groq",
        }
        with patch.dict(os.environ, env, clear=True):
            with patch("backend.hosted_language.httpx.Client", side_effect=clients):
                result = generate_reply("Explique FlyBrain", {"core": "FlyBrain"})
        self.assertEqual(result["text"], "Resposta online")
        self.assertEqual(result["provider"], "groq")
        self.assertEqual(len(calls), 2)
        self.assertIn("generativelanguage.googleapis.com", calls[0][0])
        self.assertIn("api.groq.com", calls[1][0])
        self.assertNotIn("gemini-secret", str(result))
        self.assertNotIn("groq-secret", str(result))

    def test_paid_model_override_is_skipped_without_explicit_opt_in(self):
        calls = []
        client = FakeClient(FakeResponse(200, {"choices": [{"message": {"content": "paid"}}]}), calls)
        env = {
            "GROQ_API_KEY": "secret",
            "GROQ_MODEL": "a-paid-model",
            "ULTRON_AI_PROVIDER_ORDER": "groq",
            "ULTRON_ALLOW_PAID_AI": "0",
        }
        with patch.dict(os.environ, env, clear=True):
            with patch("backend.hosted_language.httpx.Client", return_value=client):
                self.assertIsNone(generate_reply("oi", {}))
        self.assertEqual(calls, [])

    def test_malformed_or_failed_provider_returns_local_fallback(self):
        client = FakeClient(FakeResponse(503, {"error": "unavailable"}), [])
        with patch.dict(os.environ, {"GROQ_API_KEY": "secret", "ULTRON_AI_PROVIDER_ORDER": "groq"}, clear=True):
            with patch("backend.hosted_language.httpx.Client", return_value=client):
                self.assertIsNone(generate_reply("oi", {}))


if __name__ == "__main__":
    unittest.main()
