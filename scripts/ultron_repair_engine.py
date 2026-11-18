"""Deterministic, bounded repair experiment for ULTRON.

Only applies Ruff's documented safe fixes. Every attempt gets an audit trail
and a Git checkpoint. Failed candidates are restored to the checkpoint.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

MAX_FILES = int(os.environ.get("ULTRON_MAX_REPAIR_FILES", "30"))
MAX_DIFF_LINES = int(os.environ.get("ULTRON_MAX_REPAIR_LINES", "1000"))
TEST_TIMEOUT_SECONDS = int(os.environ.get("ULTRON_TEST_TIMEOUT_SECONDS", "600"))
CYCLE_BUDGET_SECONDS = int(os.environ.get("ULTRON_CYCLE_BUDGET_SECONDS", "1800"))
_started = time.monotonic()
_deadline = _started + CYCLE_BUDGET_SECONDS


def audit(path: Path, stage: str, outcome: str, **details: object) -> None:
    """Append secret-free event records; never dump environment values."""
    path.parent.mkdir(parents=True, exist_ok=True)
    event = {
        "schema_version": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "run_id": os.environ.get("GITHUB_RUN_ID", "local"),
        "commit": os.environ.get("GITHUB_SHA", "local"),
        "stage": stage,
        "outcome": outcome,
        "elapsed_seconds": round(time.monotonic() - _started, 3),
        "budget_remaining_seconds": max(0, int(_deadline - time.monotonic())),
        "details": details,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")


def remaining_seconds() -> int:
    return max(0, int(_deadline - time.monotonic()))


def command(args: list[str], timeout: int = TEST_TIMEOUT_SECONDS) -> dict:
    remaining = remaining_seconds()
    if remaining <= 0:
        return {"returncode": 124, "stdout": "", "stderr": "cycle budget exhausted"}
    try:
        result = subprocess.run(args, text=True, capture_output=True, timeout=max(1, min(timeout, remaining)))
        return {"returncode": result.returncode, "stdout": result.stdout[-20000:], "stderr": result.stderr[-20000:]}
    except subprocess.TimeoutExpired as exc:
        return {
            "returncode": 124,
            "stdout": (exc.stdout or "")[-20000:] if isinstance(exc.stdout, str) else "",
            "stderr": f"timeout after {min(timeout, remaining)}s",
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


def restore_checkpoint(files: list[str]) -> dict:
    """Recovery has its own short timeout and is not blocked by an exhausted work budget."""
    if not files:
        return {"returncode": 0, "stdout": "", "stderr": ""}
    try:
        result = subprocess.run(
            ["git", "restore", "--source=HEAD", "--staged", "--worktree", "--", *files],
            text=True, capture_output=True, timeout=30,
        )
        return {"returncode": result.returncode, "stdout": result.stdout[-20000:], "stderr": result.stderr[-20000:]}
    except subprocess.TimeoutExpired:
        return {"returncode": 124, "stdout": "", "stderr": "checkpoint restore timed out after 30s"}


def main() -> int:
    root = Path.cwd()
    evidence = root / "reports/autonomy/repair-evidence"
    evidence.mkdir(parents=True, exist_ok=True)
    audit_path = evidence / "audit.jsonl"
    checkpoint_id = str(uuid.uuid4())
    checkpoint = command(["git", "rev-parse", "HEAD"], timeout=15)
    status = command(["git", "status", "--porcelain"], timeout=15)
    checkpoint_record = {
        "checkpoint_id": checkpoint_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "base_commit": checkpoint["stdout"].strip(),
        "working_tree_before_repair": status["stdout"].splitlines(),
        "restore_strategy": "git restore --source=HEAD --staged --worktree -- changed tracked files",
    }
    write_json(evidence / "checkpoint.json", checkpoint_record)
    audit(audit_path, "checkpoint_created", "ok", checkpoint_id=checkpoint_id,
          base_commit=checkpoint_record["base_commit"],
          preexisting_changes=len(checkpoint_record["working_tree_before_repair"]))

    baseline = command([sys.executable, "-m", "unittest", "discover", "-v"])
    audit(audit_path, "baseline_tests", "pass" if baseline["returncode"] == 0 else "fail",
          returncode=baseline["returncode"])
    ruff = {"returncode": 125, "stdout": "", "stderr": "skipped: baseline tests failed"}
    files: list[str] = []
    file_count, line_count = 0, 0
    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "checkpoint": checkpoint_record,
        "repair_type": "ruff_safe_fixes_only",
        "baseline_tests": baseline,
        "repair_tool": ruff,
        "changed_files": [],
        "changed_file_count": 0,
        "changed_line_count": 0,
        "budgets": {"max_files": MAX_FILES, "max_changed_lines": MAX_DIFF_LINES,
                    "cycle_seconds": CYCLE_BUDGET_SECONDS, "test_timeout_seconds": TEST_TIMEOUT_SECONDS},
        "candidate_ready": False,
        "final_tests": None,
        "final_lint": None,
        "rollback": None,
        "decision": "",
    }

    if baseline["returncode"] != 0:
        report["decision"] = "Baseline tests failed; repair was not attempted."
        audit(audit_path, "repair_skipped", "baseline_failed")
    elif remaining_seconds() <= 0:
        report["decision"] = "Cycle budget exhausted before repair; no candidate was produced."
        audit(audit_path, "repair_skipped", "budget_exhausted")
    else:
        ruff = command(["ruff", "check", "--fix", "--output-format", "json", "."], timeout=120)
        report["repair_tool"] = ruff
        files = changed_files()
        file_count, line_count = diff_stats()
        report["changed_files"] = files
        report["changed_file_count"] = file_count
        report["changed_line_count"] = line_count
        audit(audit_path, "repair_attempt", "changed" if files else "no_change",
              returncode=ruff["returncode"], changed_files=file_count, changed_lines=line_count)

        if not files:
            report["decision"] = "No safe automatic fix was available; no branch will be published."
        elif file_count > MAX_FILES or line_count > MAX_DIFF_LINES:
            rollback = restore_checkpoint(files)
            report["rollback"] = rollback
            report["changed_files"] = []
            report["decision"] = "Candidate exceeded the diff budget and was discarded."
            audit(audit_path, "rollback", "ok" if rollback["returncode"] == 0 else "failed",
                  reason="diff_budget_exceeded", returncode=rollback["returncode"])
            if rollback["returncode"] != 0:
                raise RuntimeError("Checkpoint restoration failed after diff-budget rejection.")
        elif remaining_seconds() <= 0:
            rollback = restore_checkpoint(files)
            report["rollback"] = rollback
            report["changed_files"] = []
            report["decision"] = "Cycle budget exhausted; candidate restored to checkpoint."
            audit(audit_path, "rollback", "ok" if rollback["returncode"] == 0 else "failed",
                  reason="cycle_budget_exhausted", returncode=rollback["returncode"])
            if rollback["returncode"] != 0:
                raise RuntimeError("Checkpoint restoration failed after budget exhaustion.")
        else:
            patch = subprocess.run(["git", "diff", "--no-ext-diff", "--"], text=True,
                                   capture_output=True, timeout=min(30, max(1, remaining_seconds())))
            (evidence / "candidate.patch").write_text(patch.stdout, encoding="utf-8")
            final = command([sys.executable, "-m", "unittest", "discover", "-v"])
            report["final_tests"] = final
            final_lint = command(["ruff", "check", ".", "--output-format", "json"], timeout=120)
            report["final_lint"] = final_lint
            if final["returncode"] == 0 and final_lint["returncode"] == 0:
                report["candidate_ready"] = True
                report["decision"] = "Safe Ruff patch retained: regression tests and final lint passed."
                audit(audit_path, "candidate_validation", "pass",
                      tests_returncode=final["returncode"], lint_returncode=final_lint["returncode"])
            else:
                rollback = restore_checkpoint(files)
                report["rollback"] = rollback
                report["changed_files"] = []
                report["decision"] = "Patch failed regression or lint gate and was restored to checkpoint."
                audit(audit_path, "rollback", "ok" if rollback["returncode"] == 0 else "failed",
                      reason="validation_failed", tests_returncode=final["returncode"],
                      lint_returncode=final_lint["returncode"], restore_returncode=rollback["returncode"])
                if rollback["returncode"] != 0:
                    raise RuntimeError("Checkpoint restoration failed after validation failure.")

    report["elapsed_seconds"] = round(time.monotonic() - _started, 3)
    report["budget_remaining_seconds"] = remaining_seconds()
    write_json(evidence / "repair.json", report)
    audit(audit_path, "cycle_repair_finished",
          "candidate_ready" if report["candidate_ready"] else "no_candidate",
          decision=report["decision"], elapsed_seconds=report["elapsed_seconds"])

    summary = [
        "# ULTRON repair experiment", "",
        f"- Decision: {report['decision']}",
        f"- Checkpoint: {checkpoint_id} ({checkpoint_record['base_commit'][:12]})",
        f"- Baseline tests: {'PASS' if baseline['returncode'] == 0 else 'FAIL'}",
        f"- Final tests: {'PASS' if report['final_tests'] and report['final_tests']['returncode'] == 0 else ('NOT RUN' if report['final_tests'] is None else 'FAIL')}",
        f"- Changed files: {len(report['changed_files'])}",
        f"- Changed lines: {line_count if report['candidate_ready'] else 0}",
        f"- Limits: {MAX_FILES} files / {MAX_DIFF_LINES} changed lines / {CYCLE_BUDGET_SECONDS}s cycle / {TEST_TIMEOUT_SECONDS}s per test run",
        "- Audit: audit.jsonl",
        f"- Rollback: {'completed' if report['rollback'] and report['rollback']['returncode'] == 0 else ('failed' if report['rollback'] else 'not required')}",
        "", "## Changed files",
        *[f"- {name}" for name in report["changed_files"]],
        "", "The candidate is isolated and test-gated; no product release is performed.",
    ]
    (evidence / "repair.md").write_text("\n".join(summary) + "\n", encoding="utf-8")
    print(json.dumps({key: report[key] for key in ("candidate_ready", "decision", "changed_files")}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
