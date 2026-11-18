import tempfile
import unittest
from pathlib import Path

from scripts.ultron_repair_engine import diff_stats


class RepairBudgetTests(unittest.TestCase):
    def test_empty_diff_has_zero_budget_usage(self):
        with tempfile.TemporaryDirectory() as directory:
            old = Path.cwd()
            try:
                import os
                os.chdir(directory)
                subprocess = __import__("subprocess")
                subprocess.run(["git", "init", "-q"], check=True)
                self.assertEqual(diff_stats(), (0, 0))
            finally:
                os.chdir(old)


if __name__ == "__main__":
    unittest.main()
