from __future__ import annotations

import ast
import hmac
import operator
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal

from fastapi import Depends, FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from backend.agent_core import (SELF_MODEL, benchmark_cases, improvement_proposal, plan_task, rank_memories, review_response, system_instructions)
from backend.brain import run_multitask
from backend.fly_brain import FLY_BRAIN, FLY_BRAIN_SOURCE, FLY_BRAIN_VERSION
from backend.flywire_runtime import status as flywire_status, runtime_loaded as flywire_runtime_loaded
from backend.local_decoder import decode_local
from backend.public_access import enforce_public_limit
from backend.web_research import search_web

APP_NAME = "ULTRON"
DATABASE_URL = os.getenv("DATABASE_URL", "")
DB_PATH = Path(os.getenv("ULTRON_DB_PATH", "ultron.db"))

app = FastAPI(title=APP_NAME, version="0.4.0", description="Assistente pessoal com memória persistente e ações seguras.")

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


init_db()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)


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


class FlyWireSimulationRequest(BaseModel):
    stimulus: Literal["sugar", "p9"]
    duration_sec: float = Field(default=0.1, ge=0.01, le=0.1)


class MultiTaskRequest(BaseModel):
    tasks: list[str] = Field(min_length=1, max_length=5)


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
    history: list[str] | None = None, neural_state: dict[str, Any] | None = None) -> str:
    """Token-free local answer path; no hosted model is called."""
    normalized = message.strip()
    lower = normalized.lower()
    if lower.startswith("/calc "):
        return f"Resultado: {calculate(normalized[6:].strip())}"
    if lower.startswith("/remember "):
        content = normalized[10:].strip()
        if not content:
            return "Escreva o que devo guardar depois de /remember."
        with connect_db() as db:
            execute(db, "INSERT INTO memories(content, created_at) VALUES (?, ?)",
                (content, datetime.now(timezone.utc).isoformat()))
        return "Anotado na memória persistente do ULTRON."
    if lower.startswith("/plan "):
        plan = plan_task(normalized[6:].strip())
        steps = "\n".join(f"{item['step']}. {item['action']}" for item in plan["steps"])
        return "\n".join([f"Plano: {plan['goal']}", f"Risco: {plan['risk']}",
            f"Aprovação humana: {'sim' if plan['human_approval_required'] else 'não'}", steps])
    if lower == "/self":
        return str(SELF_MODEL.public_dict())
    if lower.startswith("/propose "):
        return str(improvement_proposal(normalized[9:].strip()))
    return decode_local(normalized, memories or [], history or [], neural_state or {})


def answer_with_provider(message: str, memories: list[str] | None = None,
    history: list[str] | None = None, grounded_search: bool = False,
    neural_state: dict[str, Any] | None = None) -> str:
    """Legacy compatibility shim; intentionally has no provider integration."""
    if grounded_search:
        raise HTTPException(status_code=503, detail="Pesquisa web indisponível no modo local sem tokens.")
    return answer_without_provider(message, memories, history, neural_state)


def apply_learned_strategy_policy(neural_state: dict[str, Any]) -> dict[str, Any]:
    """Calibrate strategy priorities from explicit user ratings, within safe bounds.

    This never changes FlyWire synapses, model weights, security rules, or code.
    """
    with connect_db() as db:
        rows = execute(
            db,
            "SELECT role, AVG(reward) AS average_reward, COUNT(*) AS samples "
            "FROM strategy_feedback GROUP BY role",
        ).fetchall()
    adjustments: dict[str, float] = {}
    scores = neural_state.get("role_scores", {})
    for row in rows:
        role = str(row["role"])
        if role not in scores:
            continue
        samples = int(row["samples"])
        average_reward = float(row["average_reward"])
        confidence = samples / (samples + 5.0)
        adjustment = max(-0.15, min(0.15, average_reward * 0.15 * confidence))
        scores[role] = round(max(0.0, float(scores[role]) * (1.0 + adjustment)), 4)
        adjustments[role] = round(adjustment, 4)
    neural_state["policy_learning"] = {
        "method": "bounded_explicit_feedback_calibration",
        "samples_by_strategy": {str(row["role"]): int(row["samples"]) for row in rows},
        "applied_adjustments": adjustments,
        "synaptic_weights_changed": False,
        "self_modifying_code": False,
    }
    return neural_state


def execute_task_with_memory(task: str) -> str:
    with connect_db() as db:
        rows = execute(db, "SELECT content FROM memories ORDER BY id DESC LIMIT 100").fetchall()
    memories = rank_memories(task, rows, limit=5)
    neural_state = FLY_BRAIN.process(task, memories)
    return answer_without_provider(task, memories, neural_state=neural_state)


def execute_brain_cycle(goal: str, history: list[str] | None = None) -> dict[str, Any]:
    with connect_db() as db:
        rows = execute(db, "SELECT content FROM memories ORDER BY id DESC LIMIT 100").fetchall()
    memories = rank_memories(goal, rows, limit=8)
    neural_state = apply_learned_strategy_policy(FLY_BRAIN.process(goal, memories))
    answer = answer_without_provider(goal, memories, history, neural_state)
    scores = neural_state["role_scores"]
    roles = sorted(("planner", "solver", "critic"),
        key=lambda role: float(scores.get(role, 0.0)), reverse=True)
    agents = [{"role": role, "neural_priority": scores.get(role, 0.0),
        "status": "completed", "result": answer if index == 0 else
        f"Perspectiva {role}: validar pressupostos, riscos e critérios de conclusão."}
        for index, role in enumerate(roles)]
    return {"brain_version": "3.0.0-local", "neural_core": neural_state,
        "goal": goal, "agents": agents, "synthesis": answer,
        "synthesis_status": "completed",
        "execution_policy": "FlyBrain é o núcleo obrigatório; decodificador local sem APIs ou tokens externos."}


@app.get("/brain/status")
def brain_status(request: Request) -> dict[str, Any]:
    enforce_public_limit(request, "brain-status", limit=60)
    return {
        "name": APP_NAME,
        "brain_version": "3.0.0-local",
        "neural_core": {
            "name": "flywire_v783" if flywire_runtime_loaded() else "drosophila_lif_microcircuit",
            "mandatory": True,
            "version": FLY_BRAIN_VERSION,
            "source": FLY_BRAIN_SOURCE,
            "runtime": "upstream_pytorch_cpu" if flywire_runtime_loaded() else "local_cpu_lif",
            "neurons": flywire_status().get("expected_neurons") if flywire_runtime_loaded() else FLY_BRAIN.neurons_per_group * 4,
            "full_connectome_ready": flywire_status()["available"],
            "full_connectome_loaded": flywire_runtime_loaded(),
            "full_connectome": flywire_status(),
            "full_connectome_enabled_for_chat": os.getenv("ULTRON_ENABLE_FULL_FLYWIRE", "0").lower() in {"1", "true", "yes", "on"},
            "active_engine": "FlyWire v783" if flywire_runtime_loaded() else "48-neuron LIF microcircuit",
        },
        "parallel_specialists": ["planner", "solver", "critic"],
        "parallel_task_limit": 5,
        "model_configured": False,
        "language_decoder": "local_deterministic",
        "external_ai_tokens_required": False,
        "web_research_enabled": True,
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


@app.post("/brain/flywire/simulate", dependencies=[Depends(require_api_token)])
def brain_flywire_simulate(request: FlyWireSimulationRequest) -> dict[str, Any]:
    """Run a documented sensory experiment on the real FlyWire v783 connectome."""
    from backend.flywire_runtime import simulate
    try:
        return simulate(request.stimulus, request.duration_sec)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


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
    with connect_db() as db:
        execute(db, "SELECT 1")
    return {
        "name": APP_NAME,
        "status": "online",
        "version": app.version,
        "database": "postgres" if DATABASE_URL.startswith(("postgres://", "postgresql://")) else "sqlite",
        "ai_configured": False,
        "neural_core_configured": True,
        "external_ai_tokens_required": False,
        "auth_configured": bool(os.getenv("ULTRON_API_TOKEN")),
    }


@app.post("/chat")
def chat(payload: ChatRequest, request: Request) -> dict[str, str]:
    enforce_public_limit(request, "chat", limit=20)
    message = payload.message.strip()
    # Public chat must not read or write shared private memories/conversations.
    try:
        neural_state = FLY_BRAIN.process(message, [])
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if message.casefold().startswith("/research "):
        try:
            research = search_web(message[10:].strip())
            response = research["summary"]
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Pesquisa web indisponível no momento; tente novamente.") from exc
    elif message.casefold().startswith("/remember "):
        response = "A memória pessoal ficará disponível quando a identificação segura por instalação estiver concluída. Nenhum dado foi gravado."
    else:
        response = answer_without_provider(message, [], [], neural_state)
    role_scores = neural_state.get("role_scores", {})
    feedback_strategies = {role: float(role_scores.get(role, 0.0)) for role in ("planner", "solver", "critic")}
    selected_strategy = max(feedback_strategies, key=feedback_strategies.get)
    return {"reply": response, "strategy": selected_strategy}


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
        "ai_configured": False,
        "neural_core_configured": True,
        "external_ai_tokens_required": False,
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
    enforce_public_limit(request, "feedback", limit=30)
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

    return {
        "id": feedback_id,
        "stored": True,
        "used_for_model_training": False,
        "used_for_policy_calibration": False,
        "strategy": payload.strategy,
    }


@app.get("/feedback/summary", dependencies=[Depends(require_api_token)])
def feedback_summary() -> dict[str, Any]:
    with connect_db() as db:
        row = execute(db, "SELECT COUNT(*) AS total, AVG(rating) AS average_rating FROM feedback").fetchone()
    return {"total": row["total"], "average_rating": float(row["average_rating"]) if row["average_rating"] is not None else None}
