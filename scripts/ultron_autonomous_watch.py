"""Lightweight scheduled self-audit and public-source scout for ULTRON.

This job does not edit or execute downloaded code. It gathers repository health,
open work, recent workflow failures and public GitHub research leads.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://api.github.com"
REPO = os.getenv("GITHUB_REPOSITORY", "MIROKKK0/ultron")
TOKEN = os.getenv("GITHUB_TOKEN", "")
HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "ULTRON-Autonomous-Scout",
}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"


def get_json(url: str):
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=12) as response:
        return json.loads(response.read().decode("utf-8"))


def repo_scan() -> dict:
    tracked = []
    try:
        import subprocess
        tracked = subprocess.check_output(["git", "ls-files"], text=True).splitlines()
    except Exception:
        pass
    matches = []
    skip = (".github/", "vendor/", "build/", "dist/")
    for name in tracked:
        if name.startswith(skip) or not name.endswith((".py", ".swift", ".yml", ".yaml", ".md")):
            continue
        path = Path(name)
        if not path.is_file() or path.stat().st_size > 500_000:
            continue
        try:
            for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
                if re.search(r"\b(TODO|FIXME|HACK|XXX)\b", line, re.I):
                    matches.append({"file": name, "line": line_no, "marker": re.search(r"\b(TODO|FIXME|HACK|XXX)\b", line, re.I).group(1), "text": line.strip()[:180]})
        except OSError:
            continue
    return {"tracked_files": len(tracked), "maintenance_markers": matches[:80], "marker_count": len(matches)}


def main() -> int:
    now = datetime.now(timezone.utc)
    report = {
        "generated_at": now.isoformat(),
        "repository": REPO,
        "commit": os.getenv("GITHUB_SHA", "unknown"),
        "trigger": os.getenv("GITHUB_EVENT_NAME", "unknown"),
        "scope": "read-only audit and research; no source edits, merges or deployments",
        "repository_audit": repo_scan(),
        "recent_failures": [],
        "open_issues": [],
        "research_leads": [],
        "errors": [],
    }

    try:
        runs = get_json(f"{API}/repos/{REPO}/actions/runs?per_page=25").get("workflow_runs", [])
        for run in runs:
            if run.get("conclusion") == "failure":
                report["recent_failures"].append({
                    "name": run.get("name"), "branch": run.get("head_branch"),
                    "created_at": run.get("created_at"), "url": run.get("html_url"),
                })
    except Exception as exc:
        report["errors"].append(f"actions_api: {type(exc).__name__}: {exc}")

    try:
        issues = get_json(f"{API}/repos/{REPO}/issues?state=open&per_page=30")
        report["open_issues"] = [
            {"number": item.get("number"), "title": item.get("title"), "url": item.get("html_url")}
            for item in issues if "pull_request" not in item
        ]
    except Exception as exc:
        report["errors"].append(f"issues_api: {type(exc).__name__}: {exc}")

    # Search public repositories for implementation techniques, never model weights.
    try:
        found = []
        selected_query = None
        for candidate_query in ("transformer", "tokenizer", "language:python llm"):
            query = urllib.parse.urlencode({
                "q": candidate_query,
                "sort": "stars", "order": "desc", "per_page": 8,
            })
            found = get_json(f"{API}/search/repositories?{query}").get("items", [])
            if found:
                selected_query = candidate_query
                break
        report["research_query"] = selected_query
        report["research_leads"] = [
            {
                "name": item.get("full_name"),
                "description": (item.get("description") or "")[:260],
                "stars": item.get("stargazers_count", 0),
                "updated_at": item.get("updated_at"),
                "url": item.get("html_url"),
                "license": (item.get("license") or {}).get("spdx_id"),
                "warning": "Lead for human review only; inspect code, license, security and relevance before adopting.",
            }
            for item in found[:8]
        ]
    except Exception as exc:
        report["errors"].append(f"research_api: {type(exc).__name__}: {exc}")

    audit = report["repository_audit"]
    priorities = []
    if report["recent_failures"]:
        priorities.append("Investigar falhas recentes de Actions e reproduzir a causa antes de alterar código.")
    if audit["marker_count"]:
        priorities.append(f"Revisar {audit['marker_count']} marcadores TODO/FIXME/HACK/XXX e converter os relevantes em tarefas testáveis.")
    if not report["research_leads"]:
        priorities.append("A pesquisa externa falhou ou não retornou fontes; repetir em outro ciclo sem inventar resultados.")
    priorities.extend([
        "Comparar qualidade, latência e memória do modelo com conjuntos retidos, não apenas com a perda de treino.",
        "Só propor mudanças pequenas em branch isolada; exigir CI e revisão antes de produção.",
    ])
    report["priorities"] = priorities

    lines = [
        "# ULTRON — ciclo autônomo de 10 minutos",
        "",
        f"- UTC: {report['generated_at']}",
        f"- Commit: `{report['commit'][:12]}`",
        f"- Arquivos rastreados: {audit['tracked_files']}",
        f"- Marcadores de manutenção: {audit['marker_count']}",
        f"- Falhas recentes em Actions: {len(report['recent_failures'])}",
        f"- Issues abertas: {len(report['open_issues'])}",
        f"- Fontes públicas encontradas: {len(report['research_leads'])}",
        "",
        "## Próximas prioridades",
        *[f"- {item}" for item in priorities],
        "",
        "## Falhas recentes",
    ]
    lines += [f"- [{x['name']}]({x['url']}) — {x['created_at']}" for x in report["recent_failures"]] or ["- Nenhuma falha recente observada."]
    lines += ["", "## Pesquisa pública — pistas, não recomendações automáticas"]
    lines += [f"- [{x['name']}]({x['url']}) — {x['description']} (⭐ {x['stars']}, licença: {x['license'] or 'não informada'})" for x in report["research_leads"]] or ["- Nenhuma fonte verificável retornada."]
    lines += ["", "## Issues abertas"]
    lines += [f"- [#{x['number']} {x['title']}]({x['url']})" for x in report["open_issues"]] or ["- Nenhuma."]
    lines += ["", "## Guardrails", "- Este ciclo é somente leitura. Não baixa nem executa código externo.", "- Não altera pesos de produção, código, branches, PRs ou deployments.", "- Repositórios encontrados são pistas; licenças e segurança precisam de revisão."]
    if report["errors"]:
        lines += ["", "## Erros de coleta", *[f"- {item}" for item in report["errors"]]]
    markdown = "\n".join(lines) + "\n"

    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_path:
        with open(summary_path, "a", encoding="utf-8") as output:
            output.write(markdown)
    Path("ultron-autonomous-watch.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "tracked_files": audit["tracked_files"],
        "maintenance_markers": audit["marker_count"],
        "recent_failures": len(report["recent_failures"]),
        "research_leads": len(report["research_leads"]),
        "collection_errors": len(report["errors"]),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
