"""Read-only self-knowledge about ULTRON's checked-out source tree and Git history."""
from __future__ import annotations

import ast
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


def _architecture_map(root: Path, paths: list[str]) -> dict[str, Any]:
    modules: list[str] = []
    edges: set[tuple[str, str]] = set()
    routes: set[tuple[str, str, str]] = set()
    specialists: set[str] = set()
    methods = {"get", "post", "put", "patch", "delete", "options", "head"}

    for relative in paths:
        if not relative.startswith("backend/") or not relative.endswith(".py"):
            continue
        source_path = root / relative
        try:
            source = source_path.read_text(encoding="utf-8", errors="replace")
            tree = ast.parse(source, filename=relative)
        except (OSError, SyntaxError, ValueError):
            continue
        module_name = relative[:-3].replace("/", ".")
        modules.append(module_name)

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith("backend."):
                        edges.add((module_name, alias.name))
            elif isinstance(node, ast.ImportFrom):
                imported = node.module or ""
                if imported.startswith("backend."):
                    edges.add((module_name, imported))
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for decorator in node.decorator_list:
                    if not isinstance(decorator, ast.Call) or not isinstance(decorator.func, ast.Attribute):
                        continue
                    owner = decorator.func.value
                    method = decorator.func.attr.lower()
                    if not isinstance(owner, ast.Name) or owner.id != "app" or method not in methods:
                        continue
                    if decorator.args and isinstance(decorator.args[0], ast.Constant) and isinstance(decorator.args[0].value, str):
                        routes.add((method.upper(), decorator.args[0].value, node.name))
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "Specialist":
                if node.args and isinstance(node.args[0], ast.Constant) and isinstance(node.args[0].value, str):
                    specialists.add(node.args[0].value)

    return {
        "backend_modules": sorted(modules)[:250],
        "dependency_graph": {
            "node_count": len(modules),
            "edge_count": len(edges),
            "edges": [
                {"from": source, "to": target}
                for source, target in sorted(edges)[:300]
            ],
            "truncated": len(edges) > 300,
        },
        "api_routes": [
            {"method": method, "path": path, "handler": handler}
            for method, path, handler in sorted(routes)[:200]
        ],
        "api_route_count": len(routes),
        "specialists": sorted(specialists),
    }


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
    architecture = _architecture_map(project_root, paths)
    has_agent_eval = "scripts/agent_eval.py" in paths
    has_evolution_gate = ".github/workflows/agent-evolution.yml" in paths
    has_model_training = ".github/workflows/model-training.yml" in paths
    has_improvement_gate = "backend/improvement_cycle.py" in paths
    has_intent_model = "backend/intent_model.py" in paths
    has_generative_adapter = "backend/generative.py" in paths
    has_local_transformer = "backend/local_transformer_runtime.py" in paths

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
        "specialist_registry": len(architecture["specialists"]) == 6,
        "api_route_inventory": architecture["api_route_count"] > 0,
        "backend_dependency_graph": architecture["dependency_graph"]["edge_count"] > 0,
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
        "automatic_merge_to_production": False,
        "automatic_deployment": False,
        "human_review_for_production": True,
        "explanation": (
            "O ciclo atual mede e valida candidatos e pode abrir PRs; não contém "
            "um gerador autônomo geral de patches nem autorização de merge/deploy."
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
        "architecture": architecture,
        "capabilities": capabilities,
        "self_evolution": evolution,
        "limitations": [
            "A presença de um módulo não prova que esteja ligado ao app instalado.",
            "O histórico mostrado é o do checkout disponível, não de branches remotas não buscadas.",
            "O inventário não lê conteúdo de arquivos secretos nem executa código do repositório.",
            "A análise de qualidade exige testes, benchmarks e observabilidade do runtime.",
        ],
    }
