"""Deterministic, offline ULTRON capability benchmark; emits no user data."""
from __future__ import annotations
import argparse, json
from pathlib import Path
from backend.evidence_critic import review_evidence
from backend.hierarchical_planner import plan_hierarchical
from backend.tool_runtime import ToolRegistry, ToolSpec
from backend.improvement_cycle import Evaluation, compare_candidate
from backend.agent_evaluation import evaluate_search_result

def run() -> dict:
    checks = {}
    try:
        from backend.hierarchical_planner import plan_hierarchical
        plan = plan_hierarchical("Pesquisar fontes e depois comparar resultados")
        checks["hierarchical_dependencies"] = len(plan["subtasks"]) >= 2 and bool(plan["dependencies"])
        checks["scenario_simulation"] = len(plan["simulated_outcomes"]) >= 3
    except Exception:
        checks["hierarchical_dependencies"] = False
        checks["scenario_simulation"] = False
    try:
        from backend.evidence_critic import review_evidence
        critic = review_evidence("pesquisa", "Conclusão definitiva sem fontes suficientes.")
        checks["critic_flags_unverified_claims"] = bool(critic["needs_human_or_source_check"])
    except Exception:
        checks["critic_flags_unverified_claims"] = False
    try:
        from backend.agent_evaluation import evaluate_search_result
        search = evaluate_search_result("documentação Python", {"results": [
            {"title": "Python docs", "topic_overlap": .8, "relevance": .8},
            {"title": "ESPN fantasy basketball", "topic_overlap": 0, "relevance": .6},
        ]})
        checks["search_rejects_off_topic"] = search["accepted_count"] == 1 and search["rejected_count"] == 1
    except Exception:
        checks["search_rejects_off_topic"] = False
    try:
        from backend.tool_runtime import ToolRegistry, ToolSpec
        registry = ToolRegistry()
        registry.register(ToolSpec("read", lambda: {"observed": True}, True, 1))
        observation = registry.execute("read")
        checks["tool_observation"] = observation["status"] == "completed" and observation["observation"]["observed"]
        registry2 = ToolRegistry()
        registry2.register(ToolSpec("non_idempotent", lambda: (_ for _ in ()).throw(RuntimeError()), False, 2))
        failure = registry2.execute("non_idempotent")
        checks["no_unsafe_retry"] = failure["attempts"] == 1
    except Exception:
        checks["tool_observation"] = False
        checks["no_unsafe_retry"] = False
    try:
        from backend.improvement_cycle import Evaluation, compare_candidate
        base = Evaluation(.8, 0, 0, 100)
        good = compare_candidate(base, Evaluation(.82, 0, 0, 110))
        bad = compare_candidate(base, Evaluation(.9, 1, 0, 110))
        checks["promotion_gate"] = good["promotion"] == "eligible_for_pr" and bad["promotion"] == "rejected"
    except Exception:
        checks["promotion_gate"] = False
    passed = sum(bool(value) for value in checks.values())
    return {"benchmark": "ultron-agent-ptbr-v1", "score": round(passed / len(checks), 4),
            "passed": passed == len(checks), "checks": checks,
            "privacy": "no prompts, responses, identifiers or personal content recorded"}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    args = parser.parse_args()
    report = run()
    rendered = json.dumps(report, ensure_ascii=False, indent=2)
    print(rendered)
    if args.output:
        Path(args.output).write_text(rendered + "\n", encoding="utf-8")
    raise SystemExit(0 if report["passed"] else 1)
