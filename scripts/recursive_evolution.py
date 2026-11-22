"""Generate and critically review ULTRON code-evolution candidates."""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
ALLOWED = ("ultron.py", "ultron_core.py", "mcp/", "backend/", "tests/", "ios/", "docs/", "skills/", "training/")


def api_chat(messages: list[dict], temperature: float = 0.2) -> str:
    key = os.getenv("ULTRON_LLM_API_KEY")
    if not key:
        raise RuntimeError("ULTRON_LLM_API_KEY não configurada.")
    base = os.getenv("ULTRON_LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/")
    model = os.getenv("ULTRON_LLM_MODEL", "gpt-4o-mini")
    response = requests.post(
        base + "/chat/completions",
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        json={"model": model, "messages": messages, "temperature": temperature},
        timeout=90,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"] or ""


def web_research(objective: str) -> str:
    """Best-effort public research; never blocks local tests or logs credentials."""
    try:
        response = requests.get(
            "https://html.duckduckgo.com/html/",
            params={"q": objective + " documentation best practices"},
            headers={"User-Agent": "ULTRON-Evolution/1.0"},
            timeout=12,
        )
        response.raise_for_status()
        html = response.text[:30000]
        snippets = re.findall(r'<a[^>]+class="result__a"[^>]*>(.*?)</a>|<a[^>]+class="result__snippet"[^>]*>(.*?)</a>', html)
        cleaned = []
        for pair in snippets[:8]:
            value = re.sub(r"<[^>]+>", " ", pair[0] or pair[1])
            value = re.sub(r"\s+", " ", value).strip()
            if value:
                cleaned.append(value)
        return "\n".join(cleaned)[:4000] or "Pesquisa pública sem resultados extraíveis."
    except Exception as exc:
        return f"Pesquisa indisponível ({type(exc).__name__}); continuar apenas com evidências do repositório."


def snapshot() -> str:
    chunks = []
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or ".git" in path.parts or path.name in {".env", ".env.local"}:
            continue
        if path.suffix not in {".py", ".md", ".swift", ".yml", ".yaml"}:
            continue
        rel = path.relative_to(ROOT).as_posix()
        if rel.startswith((".github/", "secrets/")):
            continue
        try:
            content = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        chunks.append(f"\n--- {rel} ---\n{content[:5000]}")
        if sum(map(len, chunks)) > 45000:
            break
    return "".join(chunks)


def extract_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        raise ValueError("O modelo não retornou JSON.")
    return json.loads(match.group(0))


def generate(objective: str) -> None:
    research = web_research(objective)
    prompt = (
        "Você é o engenheiro de evolução do ULTRON. Gere UMA melhoria pequena, verificável e "
        "compatível com a arquitetura existente. Retorne somente JSON com summary e patch. "
        "patch deve ser um unified diff aplicável por git apply. Não edite workflows, segredos, "
        "permissões, autenticação, avaliador congelado ou arquivos fora dos caminhos permitidos. "
        "Não remova testes. Inclua testes para o comportamento novo. Não alegue validação ainda.\n"
        f"OBJETIVO: {objective}\nPESQUISA PÚBLICA: {research}\nREPOSITÓRIO:\n{snapshot()}"
    )
    result = extract_json(api_chat([{"role": "system", "content": "Produza patches mínimos e seguros."},
                                    {"role": "user", "content": prompt}]))
    patch = result.get("patch", "")
    if not patch or len(patch) > 60000:
        raise ValueError("Patch vazio ou maior que 60 KB.")
    paths = re.findall(r"^\+\+\+ b/(.+)$", patch, re.M)
    if not paths or any(not any(p == allowed or p.startswith(allowed) for allowed in ALLOWED) for p in paths):
        raise ValueError("O patch tenta alterar caminhos não permitidos.")
    patch_path = Path("/tmp/ultron-evolution.patch")
    patch_path.write_text(patch, encoding="utf-8")
    subprocess.run(["git", "apply", "--check", str(patch_path)], cwd=ROOT, check=True)
    subprocess.run(["git", "apply", str(patch_path)], cwd=ROOT, check=True)
    subprocess.run(["git", "diff", "--check"], cwd=ROOT, check=True)
    Path("/tmp/ultron-evolution-summary.json").write_text(
        json.dumps({"summary": result.get("summary", "Melhoria proposta"), "changed_paths": paths}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(json.dumps({"applied": True, "summary": result.get("summary"), "changed_paths": paths}, ensure_ascii=False))


def review(test_report: str, candidate_eval: str, baseline_eval: str) -> None:
    report = Path(test_report).read_text(encoding="utf-8")
    candidate = json.loads(Path(candidate_eval).read_text(encoding="utf-8"))
    baseline = json.loads(Path(baseline_eval).read_text(encoding="utf-8"))
    tests_passed = "FAILED" not in report and "ERROR" not in report and "OK" in report
    scores_improved = float(candidate.get("score", 0)) > float(baseline.get("score", 0))
    patch = subprocess.run(["git", "diff", "--"], cwd=ROOT, text=True, capture_output=True, check=True).stdout[:30000]
    critic = api_chat([
        {"role": "system", "content": "Você é o crítico técnico do ULTRON. Seja rigoroso. Responda JSON: {decision: approve|reject, reasons: [...]}."},
        {"role": "user", "content": (
            f"TESTES_PASSARAM={tests_passed}; SCORE_BASELINE={baseline.get('score')}; "
            f"SCORE_CANDIDATO={candidate.get('score')}; MELHOROU={scores_improved}\n"
            f"RELATÓRIO:\n{report[-12000:]}\nPATCH:\n{patch}\n"
            "Aprove somente se testes passaram, score melhorou e não há regressão ou mudança perigosa."
        )},
    ])
    verdict = extract_json(critic)
    eligible = tests_passed and scores_improved and verdict.get("decision") == "approve"
    output = {"eligible_for_review": eligible, "tests_passed": tests_passed,
              "baseline_score": baseline.get("score"), "candidate_score": candidate.get("score"),
              "critic": verdict}
    Path("/tmp/ultron-review.json").write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(output, ensure_ascii=False))
    if not eligible:
        raise SystemExit("Candidato não elegível para revisão: gate não passou.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--generate", action="store_true")
    parser.add_argument("--review", action="store_true")
    parser.add_argument("--objective", default="")
    parser.add_argument("--test-report", default="/tmp/ultron-test-report.txt")
    parser.add_argument("--candidate-eval", default="/tmp/ultron-agent-evaluation.json")
    parser.add_argument("--baseline-eval", default="/tmp/ultron-baseline-evaluation.json")
    args = parser.parse_args()
    if args.generate:
        generate(args.objective or "Escolha a melhoria técnica de maior impacto comprovável.")
    elif args.review:
        review(args.test_report, args.candidate_eval, args.baseline_eval)
    else:
        parser.error("Use --generate ou --review.")
