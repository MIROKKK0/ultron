from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "recursive_evolution.py"
SPEC = importlib.util.spec_from_file_location("recursive_evolution", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(MODULE)


class RecursiveEvolutionTests(unittest.TestCase):
    def test_patch_accepts_backend_and_test_changes(self):
        diff = (
            "diff --git a/backend/example.py b/backend/example.py\n"
            "index 1111111..2222222 100644\n"
            "--- a/backend/example.py\n+++ b/backend/example.py\n"
            "@@ -1 +1 @@\n-old\n+new\n"
            "diff --git a/tests/test_example.py b/tests/test_example.py\n"
            "new file mode 100644\n"
            "--- /dev/null\n+++ b/tests/test_example.py\n"
            "@@ -0,0 +1 @@\n+import unittest\n"
        )
        self.assertEqual(
            MODULE.validate_patch(diff),
            ["backend/example.py", "tests/test_example.py"],
        )

    def test_patch_rejects_workflow_and_secret_paths(self):
        for path in (".github/workflows/deploy.yml", "backend/secrets/token.py", "../outside.py", "backend/app.py", "scripts/agent_eval_frozen.py", "tests/test_recursive_evolution.py"):
            diff = f"diff --git a/{path} b/{path}\n"
            with self.subTest(path=path), self.assertRaises(RuntimeError):
                MODULE.validate_patch(diff)

    def test_patch_rejects_deletion_and_binary_changes(self):
        deleted = (
            "diff --git a/backend/old.py b/backend/old.py\n"
            "deleted file mode 100644\n"
        )
        binary = (
            "diff --git a/backend/model.bin b/backend/model.bin\n"
            "GIT binary patch\n"
        )
        with self.assertRaises(RuntimeError):
            MODULE.validate_patch(deleted)
        with self.assertRaises(RuntimeError):
            MODULE.validate_patch(binary)

    def test_patch_limits_number_of_files(self):
        diff = "".join(
            f"diff --git a/backend/file{i}.py b/backend/file{i}.py\n"
            for i in range(9)
        )
        with self.assertRaises(RuntimeError):
            MODULE.validate_patch(diff)


if __name__ == "__main__":
    unittest.main()
