import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path

from scripts.ultron_repair_engine import audit, diff_stats, restore_checkpoint


class RepairBudgetTests(unittest.TestCase):
    def test_empty_diff_has_zero_budget_usage(self):
        with tempfile.TemporaryDirectory() as directory:
            old = Path.cwd()
            try:
                os.chdir(directory)
                subprocess.run(["git", "init", "-q"], check=True)
                self.assertEqual(diff_stats(), (0, 0))
            finally:
                os.chdir(old)

    def test_audit_record_contains_run_metadata_without_environment_dump(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "audit.jsonl"
            audit(path, "test_stage", "ok", changed_files=0)
            record = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(record["stage"], "test_stage")
            self.assertEqual(record["outcome"], "ok")
            self.assertEqual(record["details"]["changed_files"], 0)
            self.assertNotIn("env", record)
            self.assertIn("budget_remaining_seconds", record)

    def test_checkpoint_restore_recovers_only_named_tracked_file(self):
        with tempfile.TemporaryDirectory() as directory:
            old = Path.cwd()
            try:
                os.chdir(directory)
                subprocess.run(["git", "init", "-q"], check=True)
                subprocess.run(["git", "config", "user.email", "ultron-tests@example.invalid"], check=True)
                subprocess.run(["git", "config", "user.name", "ULTRON tests"], check=True)
                Path("tracked.txt").write_text("checkpoint\n", encoding="utf-8")
                Path("other.txt").write_text("keep\n", encoding="utf-8")
                subprocess.run(["git", "add", "tracked.txt", "other.txt"], check=True)
                subprocess.run(["git", "commit", "-qm", "checkpoint"], check=True)
                Path("tracked.txt").write_text("candidate\n", encoding="utf-8")
                Path("other.txt").write_text("untouched\n", encoding="utf-8")

                result = restore_checkpoint(["tracked.txt"])

                self.assertEqual(result["returncode"], 0)
                self.assertEqual(Path("tracked.txt").read_text(encoding="utf-8"), "checkpoint\n")
                self.assertEqual(Path("other.txt").read_text(encoding="utf-8"), "untouched\n")
            finally:
                os.chdir(old)


if __name__ == "__main__":
    unittest.main()
