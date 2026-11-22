"""Read-only self-knowledge about ULTRON's checked-out source tree and Git history."""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any

_SECRET_PATH = re.compile(
    r"""(^|/)(?:\.env(?:\..*)?|secrets?)(?:/|$)|(?:\.pem|\.key|\.p12|\.pfx|\.mobileprovision)$""",
    re.IGNORECASE,
)
_IGNORED_DIRS = {
    ".git", ".venv", "venv", "__pycache__", ".pytest_cache",
    ".mypy_cache", "node_modules", "build", "dist", ".tox",
}
_COMPONENTS = {
    "backend": "API, raciocínio, memória, ferramentas e serviços do ULTRON",
    "ios": "cliente nativo SwiftUI para iPhone",
    "tests": "testes automatizados e regressões",
    "scripts": "benchmark, treino e ferramentas de engenharia",
    "training": "corpus, tokenizadores e experimentos de modelos",
    "docs": "arquitetura, decisões e documentação",
    ".ultron": "skills e instruções locais do agente",
    ".agents": "skills e instruções de desenvolvimento",
    ".github/workflows": "CI, treino, validação e automações",
}


def _git(root: Path, *args: str, timeout: float = 4.0) -> str | None:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            check=True, capture_output=True, text=True,
            timeout=timeout, env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"},
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return result.stdout.strip()


def _safe_path(value: str) -> bool:
    normalized = value.replace("\\", "/").lstrip("/")
    return bool(normalized) and not _SECRET_PATH.search(normalized)


def _inventory(root: Path) -> tuple[list[str], dict[str, int]]:
    paths: list[str] = []
    counts: dict[str, int] = {}
    for current, dirs, files in os.walk(root, followlinks=False):
        dirs[:] = sorted(
            name for name in dirs
            if name not in _IGNORED_DIRS and (not name.startswith(".") or name in {".github", ".ultron", ".agents"})
        )
        current_path = Path(current)
        for name in files:
            full = current_path / name
            try:
                relative = full.relative_to(root).as_posix()
            except ValueError:
                continue
            if not _safe_path(relative) or full.is_symlink():
                continue
            paths.append(relative)
    paths.sort()
    for directory in ("backend", "ios", "tests", "scripts", "training", "docs", ".ultron", ".agents"):
        counts[directory] = sum(path.startswith(directory + "/") for path in paths)
    counts["github_workflows"] = sum(path.startswith(".github/workflows/") for path in paths)
    counts["python"] = sum(path.endswith(".py") for path in paths)
    counts["swift"] = sum(path.endswith(".swift") for path in paths)
    return paths, counts


def _recent_commits(root: Path, limit: int = 12) -> list[dict[str, str]]:
    raw = _git(
        root, "log", f"-{limit}",
        "--date=short", "--pretty=format:%h%x09%cs%x09%s",
    )
    if not raw:
        return []
    result = []
    for line in raw.splitlines():
        parts = line.split("\t", 2)
        if len(parts) != 3:
            continue
        sha, date, subject = parts
        subject = "".join(ch if ch.isprintable() else " " for ch in subject).strip()[:180]
        result.append({"sha": sha[:12], "date": date[:10], "subject": subject})
    return result


def _scheduled_workflows(root: Path, paths: list[str]) -> list[dict[str, str]]:
    schedules = []
    for relative in paths:
        if not relative.startswith(".github/workflows/") or not relative.endswith((".yml", ".yaml")):
            continue
        try:
            content = (root / relative).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        pattern = r"""(?m)^\s*-\s*cron:\s*["']?([^"'\n]+)"""
        for match in re.finditer(pattern, content):
            schedules.append({"workflow": relative, "cron": match.group(1).strip()})
    return schedules


def build_project_awareness(root: str | Path | None = None) -> dict[str, Any]:
    """Return a bounded, secret-free snapshot of the checked-out ULTRON project."""
    project_root = Path(root or Path(__file__).resolve().parents[1]).resolve()
    paths, counts = _inventory(project_root)
    branch = _git(project_root, "branch", "--show-current")
    commit = _git(project_root, "rev-parse", "--short=12", "HEAD")
    status = _git(project_root, "status", "--porcelain")
    recent = _recent_commits(project_root)
    main_diff = _git(project_root, "diff", "--name-only", "main...HEAD")
    changed_from_main = (
        [line for line in main_diff.splitlines() if _safe_path(line)][:100]
        if main_diff is not None else None
    )

    workflows = _scheduled_workflows(project_root, paths)
    has_agent_eval = "scripts/agent_eval.py" in paths
    has_evolution_gate = ".github/workflows/agent-evolution.yml" in paths
    has_model_training = ".github/workflows/model-training.yml" in paths
    has_improvement_gate = "backend/improvement_cycle.py" in paths
    has_intent_model = "backend/intent_model.py" in paths
    has_generative_adapter = "backend/generative.py" in paths
    has_local_transformer = "backend/local_transformer_runtime.py" in paths
    has_recursive_evolution_worker = "scripts/recursive_evolution.py" in paths
    has_evolution_dispatch = "backend/evolution_dispatch.py" in paths
    has_recursive_evolution_skill = "skills/ultron-recursive-evolution/SKILL.md" in paths

    component_map = [
        {"path": path, "purpose": purpose, "files": counts.get(
            "github_workflows" if path == ".github/workflows" else path, 0
        )}
        for path, purpose in _COMPONENTS.items()
    ]
    capabilities = {
        "intent_classifier": has_intent_model,
        "generative_adapter_module": has_generative_adapter,
        "local_transformer_runtime_module": has_local_transformer,
        "frozen_agent_benchmark": has_agent_eval,
        "measurable_improvement_gate": has_improvement_gate,
        "automated_candidate_evaluation_workflow": has_evolution_gate,
        "scheduled_classifier_retraining_workflow": has_model_training,
        "recursive_code_evolution_worker": has_recursive_evolution_worker,
        "evolution_dispatch_api": has_evolution_dispatch,
        "recursive_evolution_skill": has_recursive_evolution_skill,
    }
    evolution = {
        "benchmark_available": has_agent_eval,
        "regression_and_improvement_gate_available": has_improvement_gate and has_agent_eval,
        "candidate_branch_evaluation_available": has_evolution_gate,
        "scheduled_retraining_workflow_present": has_model_training,
        "scheduled_retraining_crons": [
            item for item in workflows if item["workflow"].endswith("model-training.yml")
        ],
        "autonomous_code_candidate_generation": False,
        "recursive_code_evolution_worker": has_recursive_evolution_worker,
        "web_research_for_evolution": has_recursive_evolution_worker and "backend/web_research.py" in paths,
        "critic_review_for_candidates": has_recursive_evolution_worker,
        "automatic_merge_to_development": has_recursive_evolution_worker,
        "automatic_merge_to_production": False,
        "automatic_deployment": False,
        "human_review_for_production": True,
        "evolution_target": "feat/ultron-core-assistant" if has_recursive_evolution_worker else None,
        "dispatch_token_configured": bool(os.getenv("ULTRON_GITHUB_TOKEN")),
        "server_dispatch_ready": bool(has_recursive_evolution_worker and has_evolution_dispatch and os.getenv("ULTRON_GITHUB_TOKEN")),
        "workflow_ref": os.getenv("ULTRON_EVOLUTION_WORKFLOW_REF", "main"),
        "model_secrets_location": "GitHub Actions secrets; not readable by the Render process",
        "explanation": (
            "O worker pesquisa fontes públicas, inspeciona o projeto, gera patches em branches "
            "isoladas, executa testes/benchmark e faz uma segunda revisão crítica. Candidatos "
            "elegíveis podem ser incorporados ao ramo de desenvolvimento; main e deploy continuam separados."
            if has_recursive_evolution_worker else
            "O ciclo atual mede e valida candidatos existentes, sem gerador autônomo geral de patches."
        ),
    }
    return {
        "project": "ULTRON",
        "snapshot_version": 1,
        "git": {
            "branch": branch or None,
            "head": commit or None,
            "working_tree_dirty": bool(status),
            "working_tree_change_count": len(status.splitlines()) if status else 0,
            "recent_commits": recent,
            "changed_files_vs_main": changed_from_main,
            "history_available": bool(recent),
        },
        "inventory": {
            "total_files": len(paths),
            "counts": counts,
            "components": component_map,
            "tracked_source_paths": paths[:250],
        },
        "capabilities": capabilities,
        "self_evolution": evolution,
        "limitations": [
            "A presença de um módulo não prova que esteja ligado ao app instalado.",
            "O histórico mostrado é o do checkout disponível, não de branches remotas não buscadas.",
            "O inventário não lê conteúdo de arquivos secretos nem executa código do repositório.",
            "A análise de qualidade exige testes, benchmarks e observabilidade do runtime.",
        ],
    }
