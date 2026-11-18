"""Bounded ULTRON autonomy cycle: inspect, research, diagnose, and publish evidence.

This first safe agent iteration does not execute external code or modify product source.
It turns observed repository signals into a reproducible report PR.
"""
from __future__ import annotations

import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

API = "https://api.github.com"
REPO = os.environ.get("GITHUB_REPOSITORY", "MIROKKK0/ultron")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2022-11-28",
    "User-Agent": "ULTRON-Autonomous-Agent",
}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"


def api_json(path: str) -> object:
    request = urllib.request.Request(API + path, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def collect_repository_signals(root: Path) -> dict:
    markers = []
    tracked = []
    for name in sorted(root.rglob("*")):
        if not name.is_file() or any(part in {".git", ".venv", "venv", "node_modules", "build", "dist"} for part in name.parts):
            continue
        rel = name.relative_to(root).as_posix()
        if rel.startswith(".github/"):
            continue
        if name.suffix not in {".py", ".swift", ".md", ".yml", ".yaml"} or name.stat().st_size > 500_000:
            continue
        tracked.append(rel)
        try:
            lines = name.read_text(encoding="utf-8", errors="replace").splitlines()
        except OSError:
            continue
        for number, line in enumerate(lines, 1):
            match = re.search(r"\b(TODO|FIXME|HACK|XXX)\b", line, re.I)
            if match:
                markers.append({
                    "file": rel, "line": number, "marker": match.group(1).upper(),
                    "text": line.strip()[:180],
                })
    return {"files_scanned": len(tracked), "maintenance_markers": markers[:100]}


def collect_github_signals() -> dict:
    failures = []
    issues = []
    research = []
    errors = []
    try:
        runs = api_json(f"/repos/{REPO}/actions/runs?per_page=30").get("workflow_runs", [])
        for run in runs:
            if run.get("conclusion") == "failure":
                failures.append({
                    "name": run.get("name"), "branch": run.get("head_branch"),
                    "sha": (run.get("head_sha") or "")[:12],
                    "created_at": run.get("created_at"), "url": run.get("html_url"),
                })
    except Exception as exc:
        errors.append(f"actions: {type(exc).__name__}: {exc}")

    try:
        raw_issues = api_json(f"/repos/{REPO}/issues?state=open&per_page=50")
        issues = [
            {"number": item["number"], "title": item["title"], "url": item["html_url"]}
            for item in raw_issues if "pull_request" not in item
        ]
    except Exception as exc:
        errors.append(f"issues: {type(exc).__name__}: {exc}")

    # Public implementation leads only; never download or execute their code.
    try:
        query = urllib.parse.urlencode({
            "q": "language:python (agent OR evaluation OR testing)",
            "sort": "updated", "order": "desc", "per_page": 8,
        })
        items = api_json(f"/search/repositories?{query}").get("items", [])
        research = [{
            "name": item.get("full_name"),
            "description": (item.get("description") or "")[:220],
            "url": item.get("html_url"),
            "updated_at": item.get("updated_at"),
            "license": (item.get("license") or {}).get("spdx_id"),
        } for item in items]
    except Exception as exc:
        errors.append(f"research: {type(exc).__name__}: {exc}")

    return {"recent_failures": failures, "open_issues": issues, "research_leads": research, "collection_errors": errors}


def build_report(root: Path, generated_at: str | None = None) -> dict:
    local = collect_repository_signals(root)
    remote = collect_github_signals()
    priorities = []
    if remote["recent_failures"]:
        priorities.append("Reproduzir a falha mais recente em runner limpo; identificar job/step e registrar o teste que falha antes de editar.")
    if local["maintenance_markers"]:
        priorities.append("Converter marcadores TODO/FIXME em tarefas pequenas, com critério de aceitação e teste.")
    if remote["open_issues"]:
        priorities.append("Agrupar issues abertas por componente e evitar criar tarefas duplicadas.")
    if remote["research_leads"]:
        priorities.append("Revisar manualmente relevância, licença, segurança e data das referências públicas antes de adotar qualquer técnica.")
    if not priorities:
        priorities.append("Nenhum problema acionável foi confirmado nesta execução; aguardar novos sinais sem inventar correções.")
    priorities.append("Próxima fase: habilitar reparos determinísticos cobertos por testes; nenhuma alteração de produto é aplicada por este ciclo.")

    return {
        "schema_version": 1,
        "generated_at": generated_at or datetime.now(timezone.utc).isoformat(),
        "repository": REPO,
        "commit": os.environ.get("GITHUB_SHA", "local"),
        "scope": "bounded read-only investigation; no external code execution, source edits, merge or deployment",
        "local": local,
        **remote,
        "priorities": priorities,
    }


def render_markdown(report: dict) -> str:
    local = report["local"]
    lines = [
        "# ULTRON — relatório autônomo de investigação",
        "",
        f"- Gerado (UTC): {report['generated_at']}",
        f"- Commit observado: `{report['commit'][:12]}`",
        f"- Arquivos inspecionados: {local['files_scanned']}",
        f"- Marcadores encontrados: {len(local['maintenance_markers'])}",
        f"- Falhas recentes de Actions: {len(report['recent_failures'])}",
        f"- Issues abertas: {len(report['open_issues'])}",
        f"- Referências públicas: {len(report['research_leads'])}",
        "",
        "## Prioridades verificáveis",
        *[f"- {item}" for item in report["priorities"]],
        "",
        "## Falhas recentes",
    ]
    lines += [f"- [{item['name']}]({item['url']}) — branch `{item['branch']}`, SHA `{item['sha']}`, {item['created_at']}" for item in report["recent_failures"]] or ["- Nenhuma falha recente encontrada."]
    lines += ["", "## Marcadores de manutenção"]
    lines += [f"- `{item['file']}:{item['line']}` — {item['marker']}: {item['text']}" for item in local["maintenance_markers"]] or ["- Nenhum marcador encontrado."]
    lines += ["", "## Issues abertas"]
    lines += [f"- [#{item['number']} {item['title']}]({item['url']})" for item in report["open_issues"]] or ["- Nenhuma issue aberta."]
    lines += ["", "## Pesquisa pública — pistas, não recomendações"]
    lines += [f"- [{item['name']}]({item['url']}) — {item['description']} (atualizado: {item['updated_at']}; licença: {item['license'] or 'não informada'})" for item in report["research_leads"]] or ["- Nenhum resultado verificável."]
    if report["collection_errors"]:
        lines += ["", "## Falhas de coleta", *[f"- {error}" for error in report["collection_errors"]]]
    lines += [
        "", "## Limites desta versão",
        "- O agente observa sinais reais e publica um relatório auditável.",
        "- Não executa código de terceiros, não altera código-fonte, não faz merge e não implanta.",
        "- Uma referência pública não é prova de qualidade; licença e segurança exigem revisão.",
        "- Uma falha de coleta é reportada como falha, nunca convertida em resultado inventado.",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    report = build_report(Path.cwd())
    output = Path("reports/autonomy")
    output.mkdir(parents=True, exist_ok=True)
    (output / "latest.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "latest.md").write_text(render_markdown(report), encoding="utf-8")
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(render_markdown(report))
    print(json.dumps({
        "failures": len(report["recent_failures"]),
        "issues": len(report["open_issues"]),
        "research_leads": len(report["research_leads"]),
        "markers": len(report["local"]["maintenance_markers"]),
        "collection_errors": len(report["collection_errors"]),
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
