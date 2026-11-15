from __future__ import annotations

import ast
import hmac
import operator
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from backend.agent_core import (SELF_MODEL, benchmark_cases, improvement_proposal, plan_task, rank_memories, review_response, system_instructions)

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


def answer_without_provider(message: str) -> str:
    normalized = message.strip()
    lower = normalized.lower()

    if lower.startswith("/calc "):
        return f"Resultado: {calculate(normalized[6:].strip())}"
    if lower.startswith("/remember "):
        content = normalized[10:].strip()
        if not content:
            return "Escreva o que devo guardar depois de /remember."
        with connect_db() as db:
            execute(
                db,
                "INSERT INTO memories(content, created_at) VALUES (?, ?)",
                (content, datetime.now(timezone.utc).isoformat()),
            )
        return "Anotado na memória do ULTRON."
    if lower in {"/help", "ajuda", "o que você faz?"}:
        return (
            "Sou o ULTRON. Posso conversar, guardar notas com /remember texto, "
            "listar memória com /memory e calcular com /calc 12*(3+4). "
            "Ações externas exigem integração explícita e confirmação."
        )
    return (
        "Estou online, mas a IA ainda não foi configurada. "
        "Defina GOOGLE_API_KEY (Gemini) ou OPENAI_API_KEY no servidor."
    )


def answer_with_provider(message: str, memories: list[str] | None = None) -> str:
    instructions = system_instructions(memories or [])
    google_key = os.getenv("GOOGLE_API_KEY")
    openai_key = os.getenv("OPENAI_API_KEY")

    try:
        if google_key:
            from google import genai

            client = genai.Client(api_key=google_key)
            response = client.models.generate_content(
                model=os.getenv("ULTRON_GEMINI_MODEL", "gemini-2.5-flash"),
                contents=f"{instructions}\n\nSolicitação do usuário:\n{message}",
            )
            return response.text or "Não consegui gerar uma resposta agora."

        if openai_key:
            from openai import OpenAI

            client = OpenAI(api_key=openai_key)
            response = client.responses.create(
                model=os.getenv("ULTRON_MODEL", "gpt-4.1-mini"),
                instructions=instructions,
                input=message,
            )
            return response.output_text
    except Exception as exc:
        raise HTTPException(status_code=502, detail="O provedor de IA não respondeu.") from exc

    return answer_without_provider(message)


@app.get("/health")
def health() -> dict[str, Any]:
    with connect_db() as db:
        execute(db, "SELECT 1")
    return {
        "name": APP_NAME,
        "status": "online",
        "version": app.version,
        "database": "postgres" if DATABASE_URL.startswith(("postgres://", "postgresql://")) else "sqlite",
        "ai_configured": bool(os.getenv("GOOGLE_API_KEY") or os.getenv("OPENAI_API_KEY")),
        "auth_configured": bool(os.getenv("ULTRON_API_TOKEN")),
    }


@app.post("/chat", dependencies=[Depends(require_api_token)])
def chat(request: ChatRequest) -> dict[str, str]:
    message = request.message.strip()
    save_conversation("user", message)
    with connect_db() as db:
        memory_rows = execute(db, "SELECT content FROM memories ORDER BY id DESC LIMIT 100").fetchall()
    memory_items = rank_memories(message, memory_rows, limit=8)
    response = answer_with_provider(message, memory_items)
    save_conversation("assistant", response)
    return {"reply": response}


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
        "ai_configured": bool(os.getenv("GOOGLE_API_KEY") or os.getenv("OPENAI_API_KEY")),
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


@app.post("/feedback", dependencies=[Depends(require_api_token)])
def add_feedback(request: FeedbackRequest) -> dict[str, Any]:
    with connect_db() as db:
        cursor = execute(
            db,
            "INSERT INTO feedback(conversation_id, rating, comment, created_at) VALUES (?, ?, ?, ?)",
            (request.conversation_id, request.rating, request.comment.strip(), datetime.now(timezone.utc).isoformat()),
        )
        feedback_id = cursor.fetchone()["id"] if is_postgres(db) else cursor.lastrowid
    return {"id": feedback_id, "stored": True, "used_for_model_training": False}


@app.get("/feedback/summary", dependencies=[Depends(require_api_token)])
def feedback_summary() -> dict[str, Any]:
    with connect_db() as db:
        row = execute(db, "SELECT COUNT(*) AS total, AVG(rating) AS average_rating FROM feedback").fetchone()
    return {"total": row["total"], "average_rating": float(row["average_rating"]) if row["average_rating"] is not None else None}
