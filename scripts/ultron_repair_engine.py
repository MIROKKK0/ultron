"""Deterministic, bounded repair experiment for ULTRON.

Only applies Ruff's documented safe fixes. It never asks a model to invent patches.
A candidate is kept only when repository tests pass after the patch and hard diff
budgets are respected. The workflow publishes the evidence and an isolated branch.
"""
from __future__ import annotations

import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

MAX_FILES = 10
MAX_DIFF_LINES = 300
TEST_TIMEOUT_SECONDS = 300


def command(args: list[str], timeout: int = TEST_TIMEOUT_SECONDS) -> dict:
    try:
        result = subprocess.run(args, text=True, capture_output=True, timeout=timeout)
        return {
            "returncode": result.returncode,
            "stdout": result.stdout[-20000:],
            "stderr": result.stderr[-20000:],
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "returncode": 124,
            "stdout": (exc.stdout or "")[-20000:] if isinstance(exc.stdout, str) else "",
            "stderr": f"timeout after {timeout}s",
        }


def changed_files() -> list[str]:
    result = command(["git", "diff", "--name-only"], timeout=30)
    return [line for line in result["stdout"].splitlines() if line.strip()]


def diff_stats() -> tuple[int, int]:
    result = command(["git", "diff", "--numstat"], timeout=30)
    files = 0
    lines = 0
    for row in result["stdout"].splitlines():
        parts = row.split("\t")
        if len(parts) >= 3:
            files += 1
            try:
                lines += int(parts[0]) + int(parts[1])
            except ValueError:
                return MAX_FILES + 1, MAX_DIFF_LINES + 1
    return files, lines


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    root = Path.cwd()
    evidence = root / "reports/autonomy/repair-evidence"
    evidence.mkdir(parents=True, exist_ok=True)

    baseline = command([sys.executable, "-m", "unittest", "discover", "-v"])
    ruff = command(["ruff", "check", "--fix", "--output-format", "json", "."])
    files = changed_files()
    file_count, line_count = diff_stats()

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "repair_type": "ruff_safe_fixes_only",
        "baseline_tests": baseline,
        "repair_tool": ruff,
        "changed_files": files,
        "changed_file_count": file_count,
        "changed_line_count": line_count,
        "budgets": {"max_files": MAX_FILES, "max_changed_lines": MAX_DIFF_LINES},
        "candidate_ready": False,
        "final_tests": None,
        "decision": "",
    }

    if not files:
        report["decision"] = "No safe automatic fix was available; no branch will be published."
    elif file_count > MAX_FILES or line_count > MAX_DIFF_LINES:
        command(["git", "restore", "--worktree", "--", *files], timeout=30)
        report["decision"] = "Candidate exceeded the diff budget and was discarded."
        report["changed_files"] = []
    else:
        patch = command(["git", "diff", "--no-ext-diff", "--"], timeout=30)
        (evidence / "candidate.patch").write_text(patch["stdout"], encoding="utf-8")
        final = command([sys.executable, "-m", "unittest", "discover", "-v"])
        report["final_tests"] = final
        final_lint = command(["ruff", "check", ".", "--output-format", "json"], timeout=120)
        report["final_lint"] = final_lint
        if final["returncode"] == 0 and final_lint["returncode"] == 0:
            report["candidate_ready"] = True
            report["decision"] = "Safe Ruff patch retained: repository unit tests and final lint gate passed."
        else:
            command(["git", "restore", "--worktree", "--", *files], timeout=30)
            report["decision"] = "Patch failed the regression or lint gate and was discarded."
            report["changed_files"] = []

    write_json(evidence / "repair.json", report)
    summary = [
        "# ULTRON repair experiment",
        "",
        f"- Decision: {report['decision']}",
        f"- Baseline tests: {'PASS' if baseline['returncode'] == 0 else 'FAIL'}",
        f"- Final tests: {'PASS' if report['final_tests'] and report['final_tests']['returncode'] == 0 else ('NOT RUN' if report['final_tests'] is None else 'FAIL')}",
        f"- Changed files: {len(report['changed_files'])}",
        f"- Changed lines: {line_count if report['candidate_ready'] else 0}",
        f"- Limits: {MAX_FILES} files / {MAX_DIFF_LINES} changed lines / {TEST_TIMEOUT_SECONDS}s per test run",
        "",
        "## Changed files",
        *[f"- `{name}`" for name in report["changed_files"]],
        "",
        "The candidate is not a product release. It is an isolated, test-gated experiment.",
    ]
    (evidence / "repair.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("candidate_ready", "decision", "changed_files")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
