from __future__ import annotations

import ast
import hmac
import json
import operator
import os
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import StreamingResponse
from starlette.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from backend.agent_core import (SELF_MODEL, benchmark_cases, improvement_proposal, plan_task, rank_memories, review_response, system_instructions)
from backend.brain import run_multitask
from backend.cognitive_workspace import CognitiveWorkspace
from backend.evidence_critic import review_evidence
from backend.hierarchical_planner import plan_hierarchical
from backend.tool_runtime import ToolRegistry, ToolSpec
from backend.agent_evaluation import evaluate_agent_cycle, evaluate_search_result
from backend.generative import generate_reply, model_config
from backend.local_decoder import decode_local
from backend.neural_learning import ASSOCIATIVE_MEMORY, LEXICAL_ENCODER
from backend.public_access import enforce_public_limit
from backend.runtime_diagnostics import memory_snapshot
from backend.intent_model import model_status
from backend.skills import list_skills, run_intent_skill, run_named_skill
from backend.web_research import search_web

APP_NAME = "ULTRON"
DATABASE_URL = os.getenv("DATABASE_URL", "")
DB_PATH = Path(os.getenv("ULTRON_DB_PATH", "ultron.db"))

app = FastAPI(title=APP_NAME, version="0.5.0", description="Assistente pessoal com memória persistente e ações seguras.")

_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def require_api_token(authorization: str | None = Header(default=None)) -> bool:
    expected = os.getenv("ULTRON_API_TOKEN")
    if not expected:
        raise HTTPException(status_code=503, detail="Servidor ainda não configurou o token de acesso.")
    scheme, _, supplied = (authorization or "").partition(" ")
    if scheme.lower() != "bearer" or not hmac.compare_digest(supplied, expected):
        raise HTTPException(status_code=401, detail="Token de acesso inválido.")
    return True


def connect_db():
    if DATABASE_URL.startswith(("postgres://", "postgresql://")):
        import psycopg
        from psycopg.rows import dict_row
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def is_postgres(db: Any) -> bool:
    return db.__class__.__module__.startswith("psycopg")


def execute(db: Any, query: str, params: tuple = ()):
    if is_postgres(db):
        query = query.replace("?", "%s")
    return db.execute(query, params)


def init_db() -> None:
    with connect_db() as db:
        if is_postgres(db):
            execute(db, """
                CREATE TABLE IF NOT EXISTS memories (
                    id BIGSERIAL PRIMARY KEY,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            execute(db, """
                CREATE TABLE IF NOT EXISTS conversations (
                    id BIGSERIAL PRIMARY KEY,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            execute(db, """CREATE TABLE IF NOT EXISTS feedback (
                id BIGSERIAL PRIMARY KEY, conversation_id BIGINT, rating INTEGER NOT NULL,
                comment TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
            )""")
            execute(db, """CREATE TABLE IF NOT EXISTS strategy_feedback (
                id BIGSERIAL PRIMARY KEY, role TEXT NOT NULL,
                reward DOUBLE PRECISION NOT NULL, created_at TEXT NOT NULL
            )""")
            execute(db, """CREATE TABLE IF NOT EXISTS neural_learning_state (
                id INTEGER PRIMARY KEY,
                state_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""")
        else:
            execute(db, """
                CREATE TABLE IF NOT EXISTS memories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            execute(db, """
                CREATE TABLE IF NOT EXISTS conversations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL
                )
            """)
            execute(db, """CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT, conversation_id INTEGER, rating INTEGER NOT NULL,
                comment TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL
            )""")
            execute(db, """CREATE TABLE IF NOT EXISTS strategy_feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT, role TEXT NOT NULL,
                reward REAL NOT NULL, created_at TEXT NOT NULL
            )""")
            execute(db, """CREATE TABLE IF NOT EXISTS neural_learning_state (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                state_json TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )""")


def load_associative_memory() -> None:
    """Restore the bounded plasticity state from the server database."""
    with connect_db() as db:
        row = execute(db, "SELECT state_json FROM neural_learning_state WHERE id = 1").fetchone()
    if row:
        try:
            ASSOCIATIVE_MEMORY.load_state_dict(json.loads(row["state_json"]))
        except (ValueError, TypeError, KeyError, json.JSONDecodeError):
            return


def persist_associative_memory() -> None:
    state_json = json.dumps(ASSOCIATIVE_MEMORY.state_dict(), separators=(",", ":"), sort_keys=True)
    updated_at = datetime.now(timezone.utc).isoformat()
    with connect_db() as db:
        existing = execute(db, "SELECT id FROM neural_learning_state WHERE id = 1").fetchone()
        if existing:
            execute(db, "UPDATE neural_learning_state SET state_json = ?, updated_at = ? WHERE id = 1",
                    (state_json, updated_at))
        else:
            execute(db, "INSERT INTO neural_learning_state(id, state_json, updated_at) VALUES (1, ?, ?)",
                    (state_json, updated_at))



init_db()
load_associative_memory()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)
    history: list[str] = Field(default_factory=list, max_length=8)


class MemoryRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class ReviewRequest(BaseModel):
    task: str = Field(min_length=1, max_length=8000)
    response: str = Field(min_length=1, max_length=12000)


class ImprovementRequest(BaseModel):
    problem: str = Field(min_length=1, max_length=2000)


class PlanRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=2000)


class FeedbackRequest(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(default="", max_length=2000)
    conversation_id: int | None = None
    strategy: Literal["planner", "solver", "critic"] | None = None


class BrainRequest(BaseModel):
    goal: str = Field(min_length=1, max_length=4000)


class MultiTaskRequest(BaseModel):
    tasks: list[str] = Field(min_length=1, max_length=5)


class NeuralLearningRequest(BaseModel):
    context: str = Field(min_length=1, max_length=2000)
    outcome: str = Field(min_length=1, max_length=2000)
    reward: float = Field(ge=-1.0, le=1.0)


class NeuralRecallRequest(BaseModel):
    context: str = Field(min_length=1, max_length=2000)


class SkillRunRequest(BaseModel):
    skill: str = Field(min_length=1, max_length=80)
    input: str = Field(min_length=1, max_length=4000)


def _safe_math(node: ast.AST) -> float:
    if isinstance(node, ast.Expression):
        return _safe_math(node.body)
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _ALLOWED_OPERATORS:
        left, right = _safe_math(node.left), _safe_math(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 8:
            raise ValueError("Expoente muito grande.")
        return _ALLOWED_OPERATORS[type(node.op)](left, right)
    if isinstance(node, ast.UnaryOp) and type(node.op) in _ALLOWED_OPERATORS:
        return _ALLOWED_OPERATORS[type(node.op)](_safe_math(node.operand))
    raise ValueError("Expressão matemática não permitida.")


def calculate(expression: str) -> str:
    try:
        result = _safe_math(ast.parse(expression, mode="eval"))
        return str(result)
    except (SyntaxError, ValueError, ZeroDivisionError, OverflowError) as exc:
        raise ValueError("Não consegui calcular essa expressão com segurança.") from exc


def save_conversation(role: str, content: str) -> None:
    with connect_db() as db:
        execute(
            db,
            "INSERT INTO conversations(role, content, created_at) VALUES (?, ?, ?)",
            (role, content, datetime.now(timezone.utc).isoformat()),
        )


def answer_without_provider(message: str, memories: list[str] | None = None,
    history: list[str] | None = None) -> str:
    """Token-free local answer path; no hosted model is called."""
    normalized = message.strip()
    lower = normalized.lower()
    if lower.startswith("/calc "):
        return f"Resultado: {calculate(normalized[6:].strip())}"
    if lower.startswith("/remember "):
        return "A memória pessoal exige autenticação por instalação. Use a rota protegida /memory para gravar sem misturar dados entre usuários."
    if lower.startswith("/plan "):
        plan = plan_task(normalized[6:].strip())
        steps = "\n".join(f"{item['step']}. {item['action']}" for item in plan["steps"])
        return "\n".join([f"Plano: {plan['goal']}", f"Risco: {plan['risk']}",
            f"Aprovação humana: {'sim' if plan['human_approval_required'] else 'não'}", steps])
    if lower == "/self":
        return str(SELF_MODEL.public_dict())
    if lower.startswith("/propose "):
        return str(improvement_proposal(normalized[9:].strip()))
    return decode_local(normalized, memories or [], history or [])


def answer_with_provider(message: str, memories: list[str] | None = None,
    history: list[str] | None = None, grounded_search: bool = False) -> str:
    """Use the configured generative model; never silently fake a provider response."""
    if grounded_search:
        raise HTTPException(status_code=503, detail="A pesquisa deve ser executada pela ferramenta web.")
    return generate_reply(message, history, memories)


def learned_strategy_scores() -> dict[str, float]:
    """Rank local specialist strategies using bounded explicit user feedback."""
    scores = {"planner": 1.0, "solver": 1.0, "critic": 1.0, "researcher": 0.8}
    try:
        with connect_db() as db:
            rows = execute(
                db,
                "SELECT role, AVG(reward) AS average_reward, COUNT(*) AS samples "
                "FROM strategy_feedback GROUP BY role",
            ).fetchall()
    except Exception:
        # Public chat must remain responsive if the optional feedback database is down.
        return scores
    for row in rows:
        role = str(row["role"])
        if role not in scores:
            continue
        samples = int(row["samples"])
        confidence = samples / (samples + 5.0)
        adjustment = max(-0.15, min(0.15, float(row["average_reward"]) * 0.15 * confidence))
        scores[role] = round(max(0.0, scores[role] * (1.0 + adjustment)), 4)
    return scores


def execute_task_with_memory(task: str) -> str:
    with connect_db() as db:
        rows = execute(db, "SELECT content FROM memories ORDER BY id DESC LIMIT 100").fetchall()
    memories = rank_memories(task, rows, limit=5)
    return answer_without_provider(task, memories)


def execute_brain_cycle(
    goal: str,
    history: list[str] | None = None,
    *,
    include_private_memories: bool = True,
) -> dict[str, Any]:
    """Run real local planner/solver/critic tools; research intents use web search.

    Local planner, solver and critic run without neural simulation or hosted LLM.
    """
    normalized_goal = goal.strip()
    if not normalized_goal:
        raise ValueError("Informe o objetivo.")

    if include_private_memories:
        with connect_db() as db:
            rows = execute(db, "SELECT content FROM memories ORDER BY id DESC LIMIT 100").fetchall()
        memories = rank_memories(normalized_goal, rows, limit=8)
    else:
        # Public chat must never read memories belonging to another installation.
        memories = []
    scores = learned_strategy_scores()

    # Each specialist now performs its actual local function instead of returning
    # a decorative placeholder string.
    workspace = CognitiveWorkspace(capacity=7)
    workspace.publish("goal", normalized_goal, source="user", confidence=1.0, priority=1.0)
    for memory in memories[:5]:
        workspace.publish("memory", memory, source="retrieved_memory", confidence=0.65, priority=0.7)
    plan = plan_task(normalized_goal)
    hierarchy = plan_hierarchical(normalized_goal)
    plan["hierarchy"] = hierarchy
    workspace.publish("plan", json.dumps(plan, ensure_ascii=False), source="planner", confidence=0.9, priority=0.9)
    attended_context = [
        f"{entry.kind}: {entry.content}"
        for entry in workspace.attend(limit=6)
    ]
    if model_config()["configured"]:
        try:
            answer = answer_with_provider(normalized_goal, attended_context, history)
        except Exception:
            answer = answer_without_provider(normalized_goal, attended_context, history)
    else:
        answer = answer_without_provider(normalized_goal, attended_context, history)
    workspace.publish("candidate_answer", answer, source="solver", confidence=0.65, priority=0.85)
    critique = review_response(normalized_goal, answer)
    workspace.publish(
        "critique", json.dumps(critique, ensure_ascii=False),
        source="critic", confidence=0.5, priority=0.8,
    )
    outputs: dict[str, dict[str, Any]] = {
        "planner": {"status": "completed", "result": plan},
        "solver": {"status": "completed", "result": {"reply": answer}},
        "critic": {"status": "completed", "result": critique},
    }

    research_query = (
        normalized_goal[10:].strip()
        if normalized_goal.casefold().startswith("/research ")
        else _extract_research_query(normalized_goal)
    )
    research: dict[str, Any] | None = None
    if research_query:
        try:
            tool_registry = ToolRegistry()
            tool_registry.register(ToolSpec("web_search", lambda query: search_web(query), idempotent=True, max_retries=1))
            tool_execution = tool_registry.execute("web_search", query=research_query)
            if tool_execution["status"] != "completed":
                raise RuntimeError("A ferramenta de pesquisa não concluiu.")
            research = tool_execution["observation"]
            research["tool_execution"] = {
                "tool": tool_execution["tool"],
                "attempts": tool_execution["attempts"],
                "recovered": tool_execution["recovered"],
            }
            workspace.publish(
                "research", research.get("summary", "Pesquisa sem resumo"),
                source="web_research", confidence=0.75 if research.get("count", 0) else 0.2,
                priority=0.95,
            )
            outputs["researcher"] = {
                "status": "completed" if research.get("count", 0) else "no_results",
                "result": research,
            }
        except Exception as exc:
            # Do not fabricate research or let a temporary search outage erase
            # the other completed cognitive stages.
            outputs["researcher"] = {
                "status": "failed",
                "result": {"error": "Pesquisa web indisponível no momento."},
            }

    evidence_items = (research or {}).get("results", []) if isinstance(research, dict) else []
    evidence_review = review_evidence(normalized_goal, answer, evidence_items)
    critique["evidence_review"] = evidence_review
    critique["needs_human_or_source_check"] = evidence_review["needs_human_or_source_check"]
    workspace.publish("evidence_review", json.dumps(evidence_review, ensure_ascii=False),
                      source="evidence_critic", confidence=0.8, priority=0.9)

    roles = sorted(
        outputs,
        key=lambda role: float(scores.get(role, 0.0)),
        reverse=True,
    )
    agents = [
        {
            "role": role,
            "priority": float(scores.get(role, 0.0)),
            **outputs[role],
        }
        for role in roles
    ]
    if research is not None:
        research["quality_evaluation"] = evaluate_search_result(research_query or normalized_goal, research)
    synthesis = research["summary"] if research and research.get("count", 0) else answer
    if research and not research.get("count", 0):
        synthesis += "\\n\\nA pesquisa não retornou fontes verificáveis."
    cycle_payload = {"agents": agents, "research": research, "review": critique}
    cycle_evaluation = evaluate_agent_cycle(cycle_payload)
    return {
        "brain_version": "4.0.0-local-tools",
        "strategy_priorities": scores,
        "goal": normalized_goal,
        "plan": plan,
        "agents": agents,
        "research": research,
        "review": critique,
        "cognitive_workspace": workspace.snapshot(),
        "cycle_evaluation": cycle_evaluation,
        "synthesis": synthesis,
        "synthesis_status": "completed",
        "execution_policy": (
            "Planner, solver e critic executam funções locais; pesquisa usa fontes web; "
            "decodificador linguístico local sem APIs ou tokens externos."
        ),
    }


@app.get("/skills")
def skills_catalog(request: Request) -> dict[str, Any]:
    enforce_public_limit(request, "skills-catalog", limit=60)
    return {"skills": list_skills(), "execution": "built_in_python_handlers_only"}


@app.post("/skills/run", dependencies=[Depends(require_api_token)])
def skills_run(payload: SkillRunRequest) -> dict[str, Any]:
    try:
        return run_named_skill(payload.skill, payload.input)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/brain/status")
def brain_status(request: Request) -> dict[str, Any]:
    enforce_public_limit(request, "brain-status", limit=60)
    return {
        "name": APP_NAME,
        "brain_version": "5.0.0-local-tools",
        "neural_core_configured": False,
        "parallel_specialists": ["planner", "solver", "critic"],
        "parallel_task_limit": 5,
        "model_configured": model_config()["configured"],
        "generative_language_model_configured": model_config()["configured"],
        "generative_model": model_config()["model"],
        "generative_provider": model_config()["provider"],
        "language_decoder": "hosted_generative_with_local_fallback" if model_config()["configured"] else "local_deterministic_with_intent_classifier",
        "intent_model": model_status(),
        "external_ai_tokens_required": True,
        "web_research_enabled": True,
        "experimental_associative_learning": True,
        "associative_memory_persistence": "database_checkpointed",
        "memory_enabled": True,
        "autonomous_production_changes": False,
    }

@app.post("/brain/run", dependencies=[Depends(require_api_token)])
def brain_run(payload: BrainRequest) -> dict[str, Any]:
    try:
        result = execute_brain_cycle(payload.goal.strip())
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    save_conversation("user", payload.goal.strip())
    save_conversation("assistant", result["synthesis"])
    return result



@app.post("/brain/learn", dependencies=[Depends(require_api_token)])
def brain_learn(payload: NeuralLearningRequest) -> dict[str, Any]:
    """Apply a bounded experimental reward-modulated association update."""
    context = LEXICAL_ENCODER.encode(payload.context)
    outcome = LEXICAL_ENCODER.encode(payload.outcome)
    try:
        result = ASSOCIATIVE_MEMORY.observe(context, outcome, payload.reward)
        persist_associative_memory()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return {"learning": result, "method": "three_factor_reward_modulated_association",
            "language_model_weights_modified": False,
            "persistence": "database_checkpointed"}


@app.post("/brain/recall", dependencies=[Depends(require_api_token)])
def brain_recall(payload: NeuralRecallRequest) -> dict[str, Any]:
    context = LEXICAL_ENCODER.encode(payload.context)
    return {"encoded_features": len(context),
            "associations": ASSOCIATIVE_MEMORY.recall(context),
            "persistence": "database_checkpointed"}


@app.post("/brain/research")
def brain_research(payload: BrainRequest, request: Request) -> dict[str, Any]:
    enforce_public_limit(request, "web-research", limit=8)
    try:
        return search_web(payload.goal)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=503, detail="Pesquisa web indisponível no momento; tente novamente.") from exc


@app.post("/brain/multitask", dependencies=[Depends(require_api_token)])
def brain_multitask(request: MultiTaskRequest) -> dict[str, Any]:
    tasks = [task.strip() for task in request.tasks if task.strip()]
    if not tasks:
        raise HTTPException(status_code=422, detail="Informe ao menos uma tarefa válida.")
    if len(tasks) > 5:
        raise HTTPException(status_code=422, detail="O limite é de cinco tarefas paralelas.")
    if any(len(task) > 4000 for task in tasks):
        raise HTTPException(status_code=422, detail="Cada tarefa deve ter no máximo 4000 caracteres.")
    result = run_multitask(tasks, execute_task_with_memory)
    for item in result["results"]:
        if item["status"] == "completed":
            save_conversation("assistant", f"[Multitarefa] {item['task']}\n{item['result']}")
    return result


@app.get("/")
def root() -> dict[str, str]:
    return {
        "name": APP_NAME,
        "status": "online",
        "health": "/health",
        "docs": "/docs",
    }


@app.get("/health")
def health() -> dict[str, Any]:
    # Liveness must not fail because a dependency is temporarily unavailable.
    return {
        "name": APP_NAME,
        "status": "online",
        "version": app.version,
        "database": "postgres" if DATABASE_URL.startswith(("postgres://", "postgresql://")) else "sqlite",
        "ai_configured": model_config()["configured"],
        "intent_model": model_status(),
        "generative_language_model_configured": model_config()["configured"],
        "generative_model": model_config()["model"],
        "generative_provider": model_config()["provider"],
        "neural_core_configured": False,
        "external_ai_tokens_required": True,
        "auth_configured": bool(os.getenv("ULTRON_API_TOKEN")),
        "health_check": "process_liveness_only",
    }


def _extract_research_query(message: str) -> str | None:
    """Recognize ordinary Portuguese research requests without slash commands."""
    text = message.strip()
    video_patterns = (
        r"^(?:me mostre|mostre|encontre|procure|busque|quero ver)\s+(?:para mim\s+)?(?:um\s+|uns?\s+)?(?:v[ií]deos?|clipes?|gameplays?)\s+(?:(?:do|no)\s+YouTube\s+)?(?:sobre|do|da|de|no|na)?\s*(.+)$",
        r"^(?:pesquise|procure|busque|encontre)\s+(?:um\s+|uns?\s+)?(?:v[ií]deos?|clipes?|gameplays?)\s+(?:(?:do|no)\s+YouTube\s+)?(?:sobre|do|da|de|no|na)?\s*(.+)$",
    )
    for pattern in video_patterns:
        match = re.match(pattern, text, flags=re.IGNORECASE)
        if match:
            subject = match.group(1).strip(" \t?.!")
            return f"vídeos do YouTube sobre {subject}"
    patterns = (
        r"^(?:por favor[, ]*)?(?:pesquise|pesquisar|pesquisa|procure|buscar|busque|busca)(?: na internet| na web| online)?(?: sobre| por| para)?\s+(.+)$",
        r"^(?:me diga|me conte|quero saber)\s+(?:mais\s+)?sobre\s+(.+)$",
    )
    for pattern in patterns:
        match = re.match(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip(" \t?.!")
    if re.match(r"^(quem é você|quem e voce|qual seu nome|me fale sobre você|me fale sobre voce|como funciona o ultron|como usar o ultron)\b", text, re.I):
        return None
    if re.match(r"^(quem é|o que é|como funciona|qual é|quais são|quando foi|onde fica)\b", text, re.I) and len(text) >= 14:
        return text
    if re.search(r"\b(hoje|atualmente|últimas notícias|mais recente|preço atual|cotação)\b", text, re.I):
        return text
    return None


@app.post("/", include_in_schema=False)
@app.post("/chat")
def chat(payload: ChatRequest, request: Request) -> dict[str, str]:
    enforce_public_limit(request, "chat", limit=20)
    message = payload.message.strip()
    # Public chat must not read or write shared private memories/conversations.
    research_query = message[10:].strip() if message.casefold().startswith("/research ") else _extract_research_query(message)
    calculation = re.match(r"^(?:quanto é|quanto dá|calcule|calcular|resultado de)\s+(.+?)\s*[?.!]*$", message, re.I)
    # Accept a plain expression such as "1+9", without requiring a command.
    if calculation is None and re.fullmatch(r"[0-9\s.,()+*/-]+", message) and re.search(r"[+*/-]", message):
        if len(re.findall(r"\d+(?:[.,]\d+)?", message)) >= 2:
            calculation = re.match(r"^(.+)$", message)
    if research_query:
        try:
            research = search_web(research_query)
            response = research["summary"]
        except Exception:
            response = "Não consegui acessar a pesquisa na internet agora. Tente novamente em instantes; os recursos locais restantes continuam disponíveis."
    elif message.casefold() == "/brain" or message.casefold().startswith("/brain "):
        goal = message[6:].strip()
        if not goal:
            response = "Informe o objetivo depois de /brain."
        else:
            try:
                brain_result = execute_brain_cycle(
                    goal,
                    history=payload.history,
                    include_private_memories=False,
                )
                response = brain_result["synthesis"]
            except RuntimeError:
                response = "O ciclo cognitivo não pôde ser concluído agora."
    elif calculation:
        expression = calculation.group(1).replace(",", ".")
        expression = re.sub(r"\b(vezes|multiplicado por)\b", "*", expression, flags=re.I)
        expression = re.sub(r"\b(dividido por|dividido)\b", "/", expression, flags=re.I)
        expression = re.sub(r"\b(mais)\b", "+", expression, flags=re.I)
        expression = re.sub(r"\b(menos)\b", "-", expression, flags=re.I)
        try:
            response = f"O resultado é {calculate(expression)}."
        except ValueError:
            response = "Não consegui interpretar essa conta com segurança. Envie apenas a expressão matemática."
    elif message.casefold().startswith("/remember ") or re.match(r"^(lembre|lembra|guarde|anote)\s+(?:que\s+)?", message, re.I):
        response = "A memória pessoal exige autenticação por instalação. O chat público não grava dados compartilhados."
    else:
        local_skill = run_intent_skill(message)
        if local_skill:
            response = local_skill
        elif model_config()["configured"]:
            parsed_history = []
            for item in payload.history[-8:]:
                role, separator, content = item.partition(":")
                if separator and role.strip() in ("user", "assistant") and content.strip():
                    parsed_history.append({"role": role.strip(), "content": content.strip()[:1000]})
            try:
                response = generate_reply(message, parsed_history)
            except Exception:
                response = "O modelo generativo está configurado, mas falhou ao responder agora. Tente novamente; não vou substituir a resposta por uma resposta local fingindo ser IA generativa."
        else:
            response = answer_without_provider(message, [], [])
    feedback_strategies = {role: float(score) for role, score in learned_strategy_scores().items() if role in ("planner", "solver", "critic")}
    selected_strategy = max(feedback_strategies, key=feedback_strategies.get)
    return {"reply": response, "strategy": selected_strategy}


@app.post("/chat/stream")
async def chat_stream(payload: ChatRequest, request: Request) -> StreamingResponse:
    """Emit lifecycle stages from the actual request execution, then the answer."""
    async def events():
        yield "data: " + json.dumps(
            {"type": "stage", "stage": "processing"}, separators=(",", ":")
        ) + "\n\n"
        try:
            result = await run_in_threadpool(chat, payload, request)
        except HTTPException as exc:
            yield "data: " + json.dumps(
                {"type": "error", "status": exc.status_code}, separators=(",", ":")
            ) + "\n\n"
            return
        except Exception:
            yield "data: " + json.dumps(
                {"type": "error", "status": 500}, separators=(",", ":")
            ) + "\n\n"
            return

        yield "data: " + json.dumps(
            {"type": "stage", "stage": "responding"}, separators=(",", ":")
        ) + "\n\n"
        yield "data: " + json.dumps(
            {"type": "final", **result}, ensure_ascii=False, separators=(",", ":")
        ) + "\n\n"

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/runtime/status")
def runtime_status(request: Request) -> dict[str, Any]:
    """Expose process RSS and configured memory budget without heavy dependencies."""
    enforce_public_limit(request, "runtime-status", limit=60)
    try:
        budget_mb = int(os.getenv("ULTRON_MEMORY_BUDGET_MB", "512"))
    except ValueError:
        budget_mb = 512
    return {
        "name": APP_NAME,
        "memory": memory_snapshot(budget_mb),
        "intent_model": model_status(),
        "generative_model_configured": model_config()["configured"],
        "generative_model": model_config()["model"],
        "generative_provider": model_config()["provider"],
        "external_ai_providers": model_config()["configured"],
    }


@app.post("/memory", dependencies=[Depends(require_api_token)])
def add_memory(request: MemoryRequest) -> dict[str, Any]:
    content = request.content.strip()
    with connect_db() as db:
        if is_postgres(db):
            cursor = execute(
                db,
                "INSERT INTO memories(content, created_at) VALUES (?, ?) RETURNING id",
                (content, datetime.now(timezone.utc).isoformat()),
            )
            memory_id = cursor.fetchone()["id"]
        else:
            cursor = execute(
                db,
                "INSERT INTO memories(content, created_at) VALUES (?, ?)",
                (content, datetime.now(timezone.utc).isoformat()),
            )
            memory_id = cursor.lastrowid
    return {"id": memory_id, "content": content}


@app.get("/memory", dependencies=[Depends(require_api_token)])
def list_memory() -> dict[str, Any]:
    with connect_db() as db:
        rows = execute(
            db,
            "SELECT id, content, created_at FROM memories ORDER BY id DESC LIMIT 100",
        ).fetchall()
    return {"items": [dict(row) for row in rows]}


@app.delete("/memory/{memory_id}", dependencies=[Depends(require_api_token)])
def delete_memory(memory_id: int) -> dict[str, bool]:
    with connect_db() as db:
        cursor = execute(db, "DELETE FROM memories WHERE id = ?", (memory_id,))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Memória não encontrada.")
    return {"deleted": True}


@app.get("/self", dependencies=[Depends(require_api_token)])
def self_knowledge() -> dict[str, Any]:
    health = {
        "database": "postgres" if DATABASE_URL.startswith(("postgres://", "postgresql://")) else "sqlite",
        "ai_configured": model_config()["configured"],
        "intent_model": model_status(),
        "generative_language_model_configured": model_config()["configured"],
        "generative_model": model_config()["model"],
        "generative_provider": model_config()["provider"],
        "neural_core_configured": False,
        "external_ai_tokens_required": True,
        "auth_configured": bool(os.getenv("ULTRON_API_TOKEN")),
    }
    return {"identity": SELF_MODEL.public_dict(), "runtime": health}


@app.post("/reflect", dependencies=[Depends(require_api_token)])
def reflect(request: ReviewRequest) -> dict[str, Any]:
    return review_response(request.task, request.response)


@app.post("/improvement-proposals", dependencies=[Depends(require_api_token)])
def propose_improvement(request: ImprovementRequest) -> dict[str, Any]:
    return improvement_proposal(request.problem)


@app.post("/agent/plan", dependencies=[Depends(require_api_token)])
def agent_plan(request: PlanRequest) -> dict[str, Any]:
    return plan_task(request.goal)


@app.get("/benchmarks", dependencies=[Depends(require_api_token)])
def benchmarks() -> dict[str, Any]:
    return {"suite": "ultron-smoke-v1", "cases": benchmark_cases(),
            "warning": "Casos internos; não comparam inteligência entre modelos."}


@app.post("/feedback")
def add_feedback(payload: FeedbackRequest, request: Request) -> dict[str, Any]:
    # Explicit user ratings are the only public learning signal; throttle heavily.
    enforce_public_limit(request, "feedback", limit=10, window_seconds=3600)
    with connect_db() as db:
        created_at = datetime.now(timezone.utc).isoformat()
        values = (payload.conversation_id, payload.rating, payload.comment.strip(), created_at)
        if is_postgres(db):
            cursor = execute(
                db,
                "INSERT INTO feedback(conversation_id, rating, comment, created_at) VALUES (?, ?, ?, ?) RETURNING id",
                values,
            )
            feedback_id = cursor.fetchone()["id"]
        else:
            cursor = execute(
                db,
                "INSERT INTO feedback(conversation_id, rating, comment, created_at) VALUES (?, ?, ?, ?)",
                values,
            )
            feedback_id = cursor.lastrowid
        if payload.strategy:
            reward = (payload.rating - 3) / 2.0
            execute(
                db,
                "INSERT INTO strategy_feedback(role, reward, created_at) VALUES (?, ?, ?)",
                (payload.strategy, reward, created_at),
            )

    return {
        "id": feedback_id,
        "stored": True,
        "used_for_model_training": False,
        "used_for_policy_calibration": bool(payload.strategy),
        "learning_scope": "bounded_strategy_priority_only",
        "strategy": payload.strategy,
    }


@app.get("/feedback/summary", dependencies=[Depends(require_api_token)])
def feedback_summary() -> dict[str, Any]:
    with connect_db() as db:
        row = execute(db, "SELECT COUNT(*) AS total, AVG(rating) AS average_rating FROM feedback").fetchone()
    return {"total": row["total"], "average_rating": float(row["average_rating"]) if row["average_rating"] is not None else None}
