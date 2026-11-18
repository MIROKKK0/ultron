"""Test execution and decision interface owned by ULTRON."""
from dataclasses import dataclass
from pathlib import Path
import subprocess
from .governance import evaluate_evolution


@dataclass(frozen=True)
class TestResult:
    passed: bool
    returncode: int
    output: str


class EvolutionOrchestrator:
    def __init__(self, workspace: Path, test_command=("python", "-m", "unittest", "discover", "-s", "tests"),
                 timeout_seconds=180):
        self.workspace = workspace.resolve()
        self.test_command = tuple(test_command)
        self.timeout_seconds = max(1, min(int(timeout_seconds), 600))

    def validate_patch_paths(self, paths):
        if not paths:
            return False
        for raw in paths:
            candidate = (self.workspace / raw).resolve()
            if candidate == self.workspace or self.workspace not in candidate.parents:
                return False
        return True

    def run_tests(self):
        try:
            result = subprocess.run(self.test_command, cwd=self.workspace, capture_output=True,
                                    text=True, timeout=self.timeout_seconds, check=False)
            return TestResult(result.returncode == 0, result.returncode,
                              (result.stdout + "\n" + result.stderr)[-12000:])
        except subprocess.TimeoutExpired as exc:
            return TestResult(False, 124, (str(exc.stdout or "") + str(exc.stderr or ""))[-12000:] + "\nTEST_TIMEOUT")
        except OSError as exc:
            return TestResult(False, 127, str(exc))

    def decide(self, paths, tests, *, diff_valid, within_budget=True, human_review=False):
        return evaluate_evolution(paths, tests_passed=tests.passed,
                                  diff_valid=diff_valid and self.validate_patch_paths(paths),
                                  within_budget=within_budget, human_review=human_review)
