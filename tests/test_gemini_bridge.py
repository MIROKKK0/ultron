import unittest
from pathlib import Path
from unittest.mock import patch

from ultron_core.provider import ProviderConfig
from scripts.ultron_gemini_proposer import patch_paths
from ultron_core.governance import evaluate_evolution


class GeminiBridgeTests(unittest.TestCase):
    def test_gemini_provider_is_selected_without_changing_core_identity(self):
        with patch.dict("os.environ", {"ULTRON_PROVIDER": "gemini", "GEMINI_API_KEY": "test-key"}, clear=True):
            config = ProviderConfig.from_env()
        self.assertEqual(config.name, "gemini")
        self.assertEqual(config.model, "gemini-3.8-flash")
        self.assertEqual(config.api_key, "test-key")

    def test_provider_requires_key_without_exposing_it(self):
        with patch.dict("os.environ", {"ULTRON_PROVIDER": "gemini"}, clear=True):
            with self.assertRaisesRegex(ValueError, "Missing API credential"):
                ProviderConfig.from_env()

    def test_extracts_only_new_file_paths_from_unified_diff(self):
        patch_text = (
            "diff --git a/src/fix.py b/src/fix.py\n"
            "--- a/src/fix.py\n+++ b/src/fix.py\n@@ -1 +1 @@\n-a\n+b\n"
        )
        self.assertEqual(patch_paths(patch_text), ["src/fix.py"])

    def test_sensitive_paths_are_rejected_without_human_review(self):
        decision = evaluate_evolution([".github/workflows/ci.yml"],
                                      tests_passed=True, diff_valid=True)
        self.assertFalse(decision.accepted)
        self.assertIn("human_review_required", decision.reasons)

    def test_path_traversal_is_rejected(self):
        decision = evaluate_evolution(["../../outside.py"],
                                      tests_passed=True, diff_valid=True)
        self.assertFalse(decision.accepted)
        self.assertIn("path_outside_workspace", decision.reasons)


if __name__ == "__main__":
    unittest.main()
