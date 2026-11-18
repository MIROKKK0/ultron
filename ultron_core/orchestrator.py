"""Provider proposals are data; ULTRON's core owns execution and decisions."""

from dataclasses import dataclass
from pathlib import Path
import subprocess
from typing import Sequence

from .governance import EvolutionDecision, evaluate_evolution


@dataclass(frozen=True)
class TestResult:
    passed: bool
    returncode: int
    output: str


class EvolutionOrchestrator:
    def __init__(self, workspace: Path, test_command: Sequence[str] = ("python", "-m", "unittest", "discover", "-s", "tests"), timeout_seconds: int = 180):
        self.workspace = workspace.resolve()
        self.test_command = tuple(test_command)
        self.timeout_seconds = max(1, min(timeout_seconds, 600))

    def validate_patch_paths(self, paths: Sequence[str]) -> bool:
        if not paths:
            return False
        for raw in paths:
            candidate = (self.workspace / raw).resolve()
            if candidate != self.workspace and self.workspace not in candidate.parents:
                return False
        return True

    def run_tests(self) -> TestResult:
        try:
            result = subprocess.run(
                self.test_command,
                cwd=self.workspace,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
            output = (result.stdout + "\n" + result.stderr)[-12000:]
            return TestResult(result.returncode == 0, result.returncode, output)
        except subprocess.TimeoutExpired as exc:
            output = str(exc.stdout or "") + str(exc.stderr or "")
            return TestResult(False, 124, output[-12000:] + "\nTEST_TIMEOUT")
        except OSError as exc:
            return TestResult(False, 127, str(exc))

    def decide(self, paths: Sequence[str], tests: TestResult, *, diff_valid: bool, within_budget: bool = True, human_review: bool = False) -> EvolutionDecision:
        in_workspace = self.validate_patch_paths(paths)
        return evaluate_evolution(
            paths,
            tests_passed=tests.passed,
            diff_valid=diff_valid and in_workspace,
            within_budget=within_budget,
            human_review=human_review,
        )
