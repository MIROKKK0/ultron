from __future__ import annotations

import ast
import hmac
import json
import operator
import os
import re
import sqlite3
import time
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
from backend.neural_learning import ASSOCIATIVE_MEMORY, LEXICAL_ENCODER
from backend.perception_bridge import perceive
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


class NeuralLearningRequest(BaseModel):
    context: str = Field(min_length=1, max_length=2000)
    outcome: str = Field(min_length=1, max_length=2000)
    reward: float = Field(ge=-1.0, le=1.0)


class NeuralRecallRequest(BaseModel):
    context: str = Field(min_length=1, max_length=2000)


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


def execute_brain_cycle(
    goal: str,
    history: list[str] | None = None,
    *,
    include_private_memories: bool = True,
    neural_state: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Run real local planner/solver/critic tools; research intents use web search.

    FlyBrain always processes the goal first and controls specialist ordering.
    The local language decoder remains subordinate and no hosted LLM is called.
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
    current_neural_state = neural_state if neural_state is not None else FLY_BRAIN.process(normalized_goal, memories)
    neural_state = apply_learned_strategy_policy(current_neural_state)
    scores = neural_state.get("role_scores", {})

    # Each specialist now performs its actual local function instead of returning
    # a decorative placeholder string.
    plan = plan_task(normalized_goal)
    answer = answer_without_provider(normalized_goal, memories, history, neural_state)
    critique = review_response(normalized_goal, answer)
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
            research = search_web(research_query)
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

    roles = sorted(
        outputs,
        key=lambda role: float(scores.get(role, 0.0)),
        reverse=True,
    )
    agents = [
        {
            "role": role,
            "neural_priority": float(scores.get(role, 0.0)),
            **outputs[role],
        }
        for role in roles
    ]
    synthesis = research["summary"] if research and research.get("count", 0) else answer
    if research and not research.get("count", 0):
        synthesis += "\\n\\nA pesquisa não retornou fontes verificáveis."
    return {
        "brain_version": "4.0.0-local-tools",
        "neural_core": neural_state,
        "goal": normalized_goal,
        "plan": plan,
        "agents": agents,
        "research": research,
        "review": critique,
        "synthesis": synthesis,
        "synthesis_status": "completed",
        "execution_policy": (
            "FlyBrain processa primeiro e prioriza as ferramentas locais; "
            "planner, solver e critic executam funções reais; pesquisa usa fontes web; "
            "decodificador linguístico local sem APIs ou tokens externos."
        ),
    }


@app.get("/brain/status")
def brain_status(request: Request) -> dict[str, Any]:
    """Expose truthful, non-sensitive brain readiness without leaking host paths."""
    enforce_public_limit(request, "brain-status", limit=60)
    full_status = flywire_status()
    loaded = flywire_runtime_loaded()
    full_connectome_enabled = os.getenv("ULTRON_ENABLE_FULL_FLYWIRE", "0").strip().lower() in {"1", "true", "yes", "on"}
    return {
        "name": APP_NAME,
        "brain_version": "4.1.0",
        "neural_core": {
            "name": "flywire_v783" if loaded else "drosophila_lif_microcircuit",
            "mandatory": True,
            "version": FLY_BRAIN_VERSION,
            "source": FLY_BRAIN_SOURCE,
            "runtime": "upstream_pytorch_cpu" if loaded else "local_cpu_lif",
            "neurons": full_status["expected_neurons"] if loaded else FLY_BRAIN.neurons_per_group * 4,
            "microcircuit_neurons": FLY_BRAIN.neurons_per_group * 4,
            "simulation_steps": FLY_BRAIN.steps,
            "full_connectome_ready": bool(full_status["available"] and full_status.get("memory_budget", {}).get("ready", False)),
            "full_connectome_loaded": loaded,
            "full_connectome_enabled_for_chat": full_connectome_enabled,
            "full_connectome": {
                "name": full_status["connectome"],
                "expected_neurons": full_status["expected_neurons"],
                "snapshot_neurons": full_status.get("snapshot_neurons", 139255),
                "modeled_neurons": full_status.get("modeled_neurons", full_status["expected_neurons"]),
                "unmodeled_snapshot_neurons": full_status.get("unmodeled_snapshot_neurons", 139255 - full_status["expected_neurons"]),
                "model_coverage_percent": full_status.get("model_coverage_percent", round(full_status["expected_neurons"] / 139255 * 100, 2)),
                "available": bool(full_status["available"]),
                "loaded_in_memory": loaded,
                "upstream_code_present": bool(full_status["upstream_code_present"]),
                "missing_files": full_status["missing_files"],
                "missing_code_files": full_status["missing_code_files"],
                "missing_dependencies": full_status["missing_dependencies"],
                "backend": full_status["backend"],
                "memory_budget": full_status.get("memory_budget", {"ready": False, "source": "unknown"}),
            },
            "supported_full_connectome_stimuli": ["sugar", "p9"],
            "perception_bridge": "ultron_conservative_perception_v2",
            "perception_bridge_scope": ["positive feeding -> sugar", "positive locomotion -> p9"],
            "active_engine": "FlyWire v783" if loaded else "48-neuron LIF microcircuit",
            "language_generation": "separate_local_language_layer",
        },
        "learning": {
            "associative_memory": "experimental_sparse_reward_modulated",
            "persistence": "database_checkpointed",
            "modifies_flywire_synapses": False,
            "modifies_language_model_weights": False,
        },
        "parallel_specialists": ["planner", "solver", "critic"],
        "parallel_task_limit": 5,
        "language_decoder": "local_deterministic",
        "external_ai_tokens_required": False,
        "web_research_enabled": True,
        "memory_enabled": False,
        "memory_api_requires_bearer_auth": True,
        "public_chat_memory_enabled": False,
        "autonomous_production_changes": False,
        "limitations": [
            "FlyWire v783 is a sensory/motor simulator, not a text-generating model.",
            "Only explicit feeding and locomotion intents map to documented sugar and p9 stimuli; arbitrary language is not decoded by the full connectome.",
            "The perception bridge rejects negated or mixed intents and is not a general language-to-neuron encoder.",
            "The upstream Shiu simulator covers 138639 of 139255 neurons in the cited FAFB v783 snapshot; 616 snapshot neurons are outside this model.",
            "Full-connectome loading is blocked unless measured free memory meets the configured safety budget.",
            "The lightweight 48-neuron LIF circuit remains active when the full runtime is not loaded.",
        ],
    }




@app.post("/brain/perception")
def brain_perception(payload: BrainRequest, request: Request) -> dict[str, Any]:
    """Return the conservative, non-persistent language-to-connectome routing result."""
    enforce_public_limit(request, "brain-perception", limit=30)
    result = perceive(payload.goal)
    return {
        "bridge": result["bridge"],
        "intent": result["intent"],
        "connectome_stimulus": result["stimulus"],
        "connectome_mapped": result["connectome_mapped"],
        "confidence": result["confidence"],
        "matched_terms": result["matched_terms"],
        "limitation": result["limitation"],
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
            "flywire_synapses_modified": False, "language_model_weights_modified": False,
            "persistence": "database_checkpointed"}


@app.post("/brain/recall", dependencies=[Depends(require_api_token)])
def brain_recall(payload: NeuralRecallRequest) -> dict[str, Any]:
    context = LEXICAL_ENCODER.encode(payload.context)
    return {"encoded_features": len(context),
            "associations": ASSOCIATIVE_MEMORY.recall(context),
            "persistence": "database_checkpointed"}


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
    # Liveness must not fail because a dependency is temporarily unavailable.
    return {
        "name": APP_NAME,
        "status": "online",
        "version": app.version,
        "database": "postgres" if DATABASE_URL.startswith(("postgres://", "postgresql://")) else "sqlite",
        "ai_configured": False,
        "neural_core_configured": True,
        "external_ai_tokens_required": False,
        "auth_configured": bool(os.getenv("ULTRON_API_TOKEN")),
        "health_check": "process_liveness_only",
    }


def _extract_research_query(message: str) -> str | None:
    """Recognize ordinary Portuguese research requests without slash commands."""
    text = message.strip()
    patterns = (
        r"^(?:por favor[, ]*)?(?:pesquise|pesquisar|pesquisa|procure|buscar|busque|busca)(?: na internet| na web| online)?(?: sobre| por| para)?\s+(.+)$",
        r"^(?:me diga|me conte|quero saber)\s+(?:mais\s+)?sobre\s+(.+)$",
    )
    for pattern in patterns:
        match = re.match(pattern, text, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip(" \t?.!")
    if re.match(r"^(quem é|o que é|como funciona|qual é|quais são|quando foi|onde fica)\b", text, re.I) and len(text) >= 14:
        return text
    if re.search(r"\b(hoje|atualmente|últimas notícias|mais recente|preço atual|cotação)\b", text, re.I):
        return text
    return None


@app.post("/", include_in_schema=False)
@app.post("/chat")
def chat(payload: ChatRequest, request: Request) -> dict[str, Any]:
    enforce_public_limit(request, "chat", limit=20)
    request_started = time.perf_counter()
    message = payload.message.strip()
    # Public chat must not read or write shared private memories/conversations.
    try:
        brain_started = time.perf_counter()
        neural_state = FLY_BRAIN.process(message, [])
        flybrain_ms = (time.perf_counter() - brain_started) * 1000.0
        policy_started = time.perf_counter()
        neural_state = apply_learned_strategy_policy(neural_state)
        policy_ms = (time.perf_counter() - policy_started) * 1000.0
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    research_ms = 0.0
    research_query = message[10:].strip() if message.casefold().startswith("/research ") else _extract_research_query(message)
    calculation = re.match(r"^(?:quanto é|quanto dá|calcule|calcular|resultado de)\s+(.+?)\s*[?.!]*$", message, re.I)
    if research_query:
        research_started = time.perf_counter()
        try:
            research = search_web(research_query)
            response = research["summary"]
        except Exception:
            response = "Não consegui acessar a pesquisa na internet agora. Tente novamente em instantes; o núcleo FlyBrain continua ativo."
        finally:
            research_ms = (time.perf_counter() - research_started) * 1000.0
    elif message.casefold() == "/brain" or message.casefold().startswith("/brain "):
        goal = message[6:].strip()
        if not goal:
            response = "Informe o objetivo depois de /brain."
        else:
            try:
                brain_result = execute_brain_cycle(
                    goal,
                    include_private_memories=False,
                    neural_state=neural_state,
                )
                response = brain_result["synthesis"]
            except RuntimeError:
                response = "O ciclo cognitivo não pôde ser concluído agora. O núcleo FlyBrain permanece obrigatório e não será ignorado."
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
        response = "Ainda não vou gravar isso em uma memória compartilhada. A memória pessoal precisa de identificação segura por instalação; assim seus dados não ficam misturados com os de outros usuários."
    else:
        response = answer_without_provider(message, [], [], neural_state)
    role_scores = neural_state.get("role_scores", {})
    feedback_strategies = {role: float(role_scores.get(role, 0.0)) for role in ("planner", "solver", "critic")}
    selected_strategy = max(feedback_strategies, key=feedback_strategies.get)
    # Send only non-private FlyBrain control signals to the on-device language
    # engine. The server has already run FlyBrain before this payload is built.
    brain_context = {
        "core": neural_state.get("core", "drosophila_lif_microcircuit"),
        "runtime": neural_state.get("runtime", "local_cpu_lif"),
        "is_full_connectome": bool(neural_state.get("is_full_connectome", False)),
        "neurons": int(neural_state.get("neurons", FLY_BRAIN.neurons_per_group * 4)),
        "simulation_steps": int(neural_state.get("simulation_steps", FLY_BRAIN.steps)),
        "novelty": float(neural_state.get("novelty", 0.0)),
        "memory_match": float(neural_state.get("memory_match", 0.0)),
        "association_bias": float(neural_state.get("association_bias", 0.0)),
        "group_activity": neural_state.get("group_activity", {}),
        "spikes": neural_state.get("spikes", {}),
        "role_scores": feedback_strategies,
        "full_connectome_activity": ({
            "engine": neural_state["full_connectome"].get("engine"),
            "stimulus": neural_state["full_connectome"].get("stimulus"),
            "active_neurons": int(neural_state["full_connectome"].get("active_neurons", 0)),
            "spikes": int(neural_state["full_connectome"].get("spikes", 0)),
            "simulation_seconds": float(neural_state["full_connectome"].get("simulation_seconds", 0.0)),
        } if isinstance(neural_state.get("full_connectome"), dict) else None),
    }
    return {
        "reply": response,
        "strategy": selected_strategy,
        "brain_context": brain_context,
        "timings_ms": {
            "flybrain": round(flybrain_ms, 2),
            "strategy_policy": round(policy_ms, 2),
            "research": round(research_ms, 2),
            "server_total": round((time.perf_counter() - request_started) * 1000.0, 2),
        },
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
