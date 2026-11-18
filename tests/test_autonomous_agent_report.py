import tempfile
import unittest
from pathlib import Path

from scripts.ultron_autonomous_agent import render_markdown


class AutonomousAgentReportTests(unittest.TestCase):
    def test_report_never_claims_fix_when_no_issue_is_observed(self):
        report = {
            "generated_at": "2026-11-18T00:00:00+00:00",
            "commit": "abc123456789",
            "local": {"files_scanned": 3, "maintenance_markers": []},
            "recent_failures": [],
            "open_issues": [],
            "research_leads": [],
            "collection_errors": ["research: TimeoutError"],
            "priorities": ["Nenhum problema acionável foi confirmado."],
        }
        markdown = render_markdown(report)
        self.assertIn("Nenhuma falha recente encontrada.", markdown)
        self.assertIn("TimeoutError", markdown)
        self.assertIn("não altera código-fonte", markdown.lower())

    def test_report_lists_observed_failure_with_sha(self):
        report = {
            "generated_at": "2026-11-18T00:00:00+00:00",
            "commit": "abc123456789",
            "local": {"files_scanned": 1, "maintenance_markers": []},
            "recent_failures": [{
                "name": "CI", "url": "https://github.com/example/run/1",
                "branch": "main", "sha": "123456789abc", "created_at": "2026-11-18T00:00:00Z"
            }],
            "open_issues": [], "research_leads": [], "collection_errors": [],
            "priorities": ["Reproduzir falha."],
        }
        markdown = render_markdown(report)
        self.assertIn("CI", markdown)
        self.assertIn("123456789abc", markdown)


if __name__ == "__main__":
    unittest.main()
