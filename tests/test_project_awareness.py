from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from backend.project_awareness import build_project_awareness


class ProjectAwarenessTests(unittest.TestCase):
    def test_inventory_excludes_secrets_and_discovers_workflow_schedule(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "backend").mkdir()
            (root / "backend" / "app.py").write_text("app = True\n", encoding="utf-8")
            (root / ".github" / "workflows").mkdir(parents=True)
            (root / ".github" / "workflows" / "model-training.yml").write_text(
                "on:\n  schedule:\n    - cron: \"17 14 * * *\"\n",
                encoding="utf-8",
            )
            (root / ".env").write_text("SECRET=must-not-be-listed\n", encoding="utf-8")

            report = build_project_awareness(root)

            self.assertIn("backend/app.py", report["inventory"]["tracked_source_paths"])
            self.assertNotIn(".env", report["inventory"]["tracked_source_paths"])
            self.assertEqual(report["inventory"]["counts"]["github_workflows"], 1)
            self.assertEqual(
                report["self_evolution"]["scheduled_retraining_crons"],
                [{"workflow": ".github/workflows/model-training.yml", "cron": "17 14 * * *"}],
            )
            self.assertFalse(report["self_evolution"]["autonomous_code_candidate_generation"])
            self.assertFalse(report["self_evolution"]["automatic_merge_to_production"])

    def test_git_history_is_reported_without_exposing_file_contents(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            subprocess.run(["git", "init", "-b", "main", str(root)], check=True, capture_output=True)
            subprocess.run(["git", "-C", str(root), "config", "user.email", "ultron-test@example.invalid"], check=True)
            subprocess.run(["git", "-C", str(root), "config", "user.name", "ULTRON test"], check=True)
            (root / "README.md").write_text("# ULTRON\n", encoding="utf-8")
            (root / ".env").write_text("API_TOKEN=never-return-this\n", encoding="utf-8")
            subprocess.run(["git", "-C", str(root), "add", "README.md", ".env"], check=True)
            subprocess.run(["git", "-C", str(root), "commit", "-m", "initial project baseline"], check=True, capture_output=True)

            report = build_project_awareness(root)

            self.assertEqual(report["git"]["branch"], "main")
            self.assertTrue(report["git"]["history_available"])
            self.assertEqual(report["git"]["recent_commits"][0]["subject"], "initial project baseline")
            self.assertNotIn("API_TOKEN", str(report))
            self.assertNotIn(".env", report["inventory"]["tracked_source_paths"])


if __name__ == "__main__":
    unittest.main()
