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

    def test_deleted_sensitive_paths_are_still_detected(self):
        patch_text = (
            "diff --git a/.github/workflows/ci.yml b/.github/workflows/ci.yml\\n"
            "--- a/.github/workflows/ci.yml\\n"
            "+++ /dev/null\\n"
            "@@ -1 +0,0 @@\\n-old\\n"
        )
        paths = patch_paths(patch_text)
        self.assertEqual(paths, [".github/workflows/ci.yml"])
        decision = evaluate_evolution(paths, tests_passed=True, diff_valid=True)
        self.assertFalse(decision.accepted)
        self.assertIn("human_review_required", decision.reasons)

    def test_renamed_sensitive_paths_include_both_sides(self):
        patch_text = (
            "diff --git a/.env b/config/runtime.env\\n"
            "rename from .env\\n"
            "rename to config/runtime.env\\n"
        )
        self.assertEqual(patch_paths(patch_text), [".env", "config/runtime.env"])

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


    def test_request_proposal_uses_structured_json_and_configured_model(self):
        from unittest.mock import MagicMock
        from scripts.ultron_gemini_proposer import request_proposal

        message = MagicMock()
        message.content = '{"summary":"Fix bounded parser","patch":"diff --git a/src/parser.py b/src/parser.py\\n"}'
        client = MagicMock()
        client.chat.completions.create.return_value.choices = [
            MagicMock(message=message)
        ]
        with patch("scripts.ultron_gemini_proposer.build_provider", return_value=(client, "gemini-3.8-flash")):
            result = request_proposal("source context", "test failure")
        self.assertEqual(result["summary"], "Fix bounded parser")
        self.assertIn("diff --git", result["patch"])
        client.chat.completions.create.assert_called_once()
        kwargs = client.chat.completions.create.call_args.kwargs
        self.assertEqual(kwargs["model"], "gemini-3.8-flash")
        self.assertEqual(kwargs["temperature"], 0)
        self.assertEqual(kwargs["response_format"], {"type": "json_object"})

    def test_request_proposal_rejects_invalid_json_and_missing_fields(self):
        from unittest.mock import MagicMock
        from scripts.ultron_gemini_proposer import request_proposal

        for content in ("not-json", '{"summary":"missing patch"}', '{"patch":""}'):
            with self.subTest(content=content):
                message = MagicMock()
                message.content = content
                client = MagicMock()
                client.chat.completions.create.return_value.choices = [
                    MagicMock(message=message)
                ]
                with patch("scripts.ultron_gemini_proposer.build_provider", return_value=(client, "gemini-3.8-flash")):
                    with self.assertRaises((ValueError, __import__("json").JSONDecodeError)):
                        request_proposal("source context", "test failure")

    def test_request_proposal_propagates_transport_failure_for_failure_evidence(self):
        from scripts.ultron_gemini_proposer import request_proposal

        from unittest.mock import MagicMock
        client = MagicMock()
        client.chat.completions.create.side_effect = TimeoutError("simulated timeout")
        with patch("scripts.ultron_gemini_proposer.build_provider", return_value=(client, "gemini-3.8-flash")):
            with self.assertRaises(TimeoutError):
                request_proposal("source context", "test failure")


if __name__ == "__main__":
    unittest.main()
