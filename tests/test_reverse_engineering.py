import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from backend import reverse_engineering as rea


class ReverseEngineeringConfigTests(unittest.TestCase):
    def test_missing_bridge_configuration_fails_closed(self):
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(HTTPException) as raised:
                rea._bridge_config()
        self.assertEqual(raised.exception.status_code, 503)

    def test_bridge_requires_https(self):
        with patch.dict(os.environ, {
            "REA_BRIDGE_URL": "http://rea-bridge.example",
            "REA_BRIDGE_TOKEN": "x" * 40,
        }, clear=True):
            with self.assertRaises(HTTPException) as raised:
                rea._bridge_config()
        self.assertEqual(raised.exception.status_code, 503)

    def test_bridge_configuration_accepts_https(self):
        with patch.dict(os.environ, {
            "REA_BRIDGE_URL": "https://rea-bridge.example/",
            "REA_BRIDGE_TOKEN": "x" * 40,
        }, clear=True):
            self.assertEqual(
                rea._bridge_config(),
                ("https://rea-bridge.example", "x" * 40),
            )

    def test_tool_names_are_bounded_and_safe(self):
        self.assertIsNotNone(rea.TOOL_NAME.fullmatch("inspect_web_page"))
        self.assertIsNone(rea.TOOL_NAME.fullmatch("../upload"))
        self.assertIsNone(rea.TOOL_NAME.fullmatch("x" * 129))

    def test_read_only_tool_policy_blocks_mutating_tools(self):
        self.assertTrue("inspect_web_page".startswith(rea.READ_ONLY_PREFIXES))
        self.assertTrue("capture_web_screenshot" in rea.READ_ONLY_EXACT)
        self.assertFalse("delete_file".startswith(rea.READ_ONLY_PREFIXES))
        self.assertFalse("execute_command".startswith(rea.READ_ONLY_PREFIXES))


if __name__ == "__main__":
    unittest.main()
