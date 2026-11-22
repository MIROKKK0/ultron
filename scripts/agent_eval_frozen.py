"""Frozen evaluator stored on default branch; candidate code cannot rewrite its scorecard."""
from __future__ import annotations
import argparse, json, os, sys
from pathlib import Path
SOURCE_ROOT = Path(os.getenv("ULTRON_SOURCE_ROOT", Path(__file__).resolve().parents[1])).resolve()
sys.path.insert(0, str(SOURCE_ROOT))

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
    # New frozen capability checks for the private neural-memory explorer.
    # Older baselines without these capabilities score false; candidate code
    # must prove the behavior rather than receive credit from a changed threshold.
    try:
        from backend.memory_insights import analyze_memories
        memories = [
            {"id": 1, "kind": "semantic", "content": "ULTRON mantém memória local independente", "confidence": .9},
            {"id": 2, "kind": "semantic", "content": "ULTRON mantém memória local independente", "confidence": .8},
        ]
        diagnostics = analyze_memories(memories, {1: 0, 2: 0})
        checks["memory_duplicates_are_review_only"] = (
            bool(diagnostics["duplicate_candidates"])
            and diagnostics["duplicate_candidates"][0]["status"] == "candidate_review_only"
        )
        checks["memory_gaps_are_evidence_bounded"] = any(
            "não prova" in limit.lower() for limit in diagnostics["analysis_limits"]
        )
    except Exception:
        checks["memory_duplicates_are_review_only"] = False
        checks["memory_gaps_are_evidence_bounded"] = False
    try:
        from backend.specialist_agents import run_specialist
        retrieved = run_specialist("memory_retriever", {"readonly_items": [
            {"id": 17, "kind": "semantic", "source": "benchmark", "confidence": .9}
        ]})["result"]
        checks["memory_retriever_has_read_only_mode"] = (
            retrieved.get("read_only") is True
            and len(retrieved.get("items", [])) == 1
            and retrieved["items"][0].get("id") == 17
        )
    except Exception:
        checks["memory_retriever_has_read_only_mode"] = False
    try:
        from backend.project_awareness import build_project_awareness
        awareness = build_project_awareness(SOURCE_ROOT)
        counts = awareness["inventory"]["counts"]
        checks["project_inventory_is_read_only_and_structured"] = (
            awareness["project"] == "ULTRON"
            and awareness["inventory"]["total_files"] > 0
            and counts.get("backend", 0) > 0
            and counts.get("tests", 0) > 0
        )
        checks["recursive_self_evolution_worker_is_available_and_not_production"] = (
            awareness["self_evolution"]["benchmark_available"]
            and awareness["self_evolution"]["regression_and_improvement_gate_available"]
            and awareness["self_evolution"].get("recursive_code_evolution_worker") is True
            and awareness["self_evolution"].get("web_research_for_evolution") is True
            and awareness["self_evolution"].get("critic_review_for_candidates") is True
            and awareness["self_evolution"].get("automatic_merge_to_development") is True
            and awareness["self_evolution"]["automatic_merge_to_production"] is False
            and awareness["self_evolution"]["automatic_deployment"] is False
        )
    except Exception:
        checks["project_inventory_is_read_only_and_structured"] = False
        checks["self_evolution_limits_are_explicit"] = False
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
