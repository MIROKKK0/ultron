import os
import unittest
from unittest.mock import patch

from backend.generative import model_config


class GenerativeAdapterTests(unittest.TestCase):
    def test_local_mode_needs_no_external_provider_or_secret(self):
        with patch.dict(os.environ, {
            "ULTRON_LLM_API_KEY": "",
            "ULTRON_LLM_BASE_URL": "",
            "ULTRON_LLM_MODEL": "",
            "GEMINI_API_KEY": "",
        }, clear=False):
            config = model_config()
        self.assertFalse(config["configured"])
        self.assertEqual(config["provider"], "local_only")
        self.assertIsNone(config["api_key"])
        self.assertIsNone(config["model"])

    def test_external_adapter_requires_all_three_values(self):
        with patch.dict(os.environ, {
            "ULTRON_LLM_API_KEY": "test-secret",
            "ULTRON_LLM_BASE_URL": "https://example.invalid/v1",
            "ULTRON_LLM_MODEL": "test-model",
        }, clear=False):
            config = model_config()
        self.assertTrue(config["configured"])
        self.assertEqual(config["provider"], "external_openai_compatible")


if __name__ == "__main__":
    unittest.main()
