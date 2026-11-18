"""Explicit local specialist registry for ULTRON."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from backend.agent_core import improvement_proposal, plan_task, review_response
from backend.agent_evaluation import evaluate_agent_cycle
from backend.hierarchical_planner import plan_hierarchical


@dataclass(frozen=True)
class Specialist:
    role: str
    purpose: str
    handler: Callable[[dict[str, Any]], dict[str, Any]]


def _planner(payload: dict[str, Any]) -> dict[str, Any]:
    goal = str(payload.get("goal", "")).strip()
    return {"plan": plan_task(goal), "hierarchy": plan_hierarchical(goal)}


def _solver(payload: dict[str, Any]) -> dict[str, Any]:
    answer = str(payload.get("answer", "")).strip()
    if not answer:
        return {"status": "needs_input", "reason": "candidate_answer_missing"}
    return {"status": "candidate_ready", "answer": answer[:12000]}


def _critic(payload: dict[str, Any]) -> dict[str, Any]:
    return review_response(str(payload.get("goal", "")), str(payload.get("answer", "")))


def _memory_retriever(payload: dict[str, Any]) -> dict[str, Any]:
    index = payload.get("index")
    owner_id = str(payload.get("owner_id", ""))
    query = str(payload.get("query", ""))
    if index is None or not owner_id or not query:
        return {"status": "needs_input", "items": []}
    return {"status": "completed", "items": index.search(owner_id, query, limit=8)}


def _memory_curator(payload: dict[str, Any]) -> dict[str, Any]:
    proposal = str(payload.get("candidate", "")).strip()
    source_ids = payload.get("source_ids", [])
    if not proposal or not isinstance(source_ids, list) or not source_ids:
        return {"status": "needs_input", "approved": False}
    return {
        "status": "proposal_only",
        "kind": "semantic",
        "candidate": proposal[:4000],
        "source_ids": [int(value) for value in source_ids[:20]],
        "approved": False,
        "write_required": "explicit_user_or_policy_approval",
    }


def _evaluator(payload: dict[str, Any]) -> dict[str, Any]:
    return evaluate_agent_cycle(payload.get("cycle", {}))


SPECIALISTS = {
    item.role: item for item in (
        Specialist("planner", "Decomposição, dependências e critérios de conclusão.", _planner),
        Specialist("solver", "Produção de uma resposta candidata a partir de evidências.", _solver),
        Specialist("critic", "Revisão heurística e identificação de lacunas.", _critic),
        Specialist("memory_retriever", "Recuperação local de memórias por similaridade vetorial.", _memory_retriever),
        Specialist("memory_curator", "Proposição de fatos semânticos com referências de origem.", _memory_curator),
        Specialist("evaluator", "Pontuação determinística do ciclo e seus critérios.", _evaluator),
    )
}


def run_specialist(role: str, payload: dict[str, Any]) -> dict[str, Any]:
    specialist = SPECIALISTS.get(str(role))
    if specialist is None:
        raise ValueError("Especialista desconhecido.")
    if not isinstance(payload, dict):
        raise ValueError("Entrada do especialista deve ser um objeto.")
    result = specialist.handler(payload)
    return {"role": specialist.role, "purpose": specialist.purpose, "result": result}
