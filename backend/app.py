from __future__ import annotations

import ast
import operator
import os
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

APP_NAME = "ULTRON"
DB_PATH = Path(os.getenv("ULTRON_DB_PATH", "ultron.db"))

app = FastAPI(title=APP_NAME, version="0.2.0", description="Assistente pessoal com memória local e ações seguras.")

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


def connect_db() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.row_factory = sqlite3.Row
    return db


def init_db() -> None:
    with connect_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)
        db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at TEXT NOT NULL
            )
        """)


init_db()


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=8000)


class MemoryRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


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
        db.execute(
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
            db.execute(
                "INSERT INTO memories(content, created_at) VALUES (?, ?)",
                (content, datetime.now(timezone.utc).isoformat()),
            )
        return "Anotado na memória local do ULTRON."
    if lower in {"/help", "ajuda", "o que você faz?"}:
        return (
            "Sou o ULTRON. Posso conversar, guardar notas com /remember texto, "
            "listar memória com /memory e calcular com /calc 12*(3+4). "
            "Ações externas exigem integração explícita e confirmação."
        )
    return (
        "ULTRON está online. Para respostas inteligentes, configure OPENAI_API_KEY "
        "nos Secrets do ambiente. Também posso guardar notas com /remember e "
        "calcular com /calc."
    )


def answer_with_provider(message: str) -> str:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return answer_without_provider(message)

    try:
        from openai import OpenAI

        client = OpenAI(api_key=api_key)
        response = client.responses.create(
            model=os.getenv("ULTRON_MODEL", "gpt-4.1-mini"),
            instructions=(
                "Você é ULTRON, um assistente pessoal em português brasileiro. "
                "Seja claro e útil. Não alegue executar ações que não executou. "
                "Não forneça instruções para invadir sistemas, roubar credenciais, "
                "burlar assinaturas ou causar dano. Peça confirmação antes de "
                "qualquer ação externa ou irreversível."
            ),
            input=message,
        )
        return response.output_text
    except Exception as exc:
        # Do not expose credentials or raw provider errors to clients.
        raise HTTPException(status_code=502, detail="O provedor de IA não respondeu.") from exc


@app.get("/health")
def health() -> dict[str, Any]:
    return {"name": APP_NAME, "status": "online", "version": app.version}


@app.post("/chat")
def chat(request: ChatRequest) -> dict[str, str]:
    message = request.message.strip()
    save_conversation("user", message)
    response = answer_with_provider(message)
    save_conversation("assistant", response)
    return {"reply": response}


@app.post("/memory")
def add_memory(request: MemoryRequest) -> dict[str, Any]:
    content = request.content.strip()
    with connect_db() as db:
        cursor = db.execute(
            "INSERT INTO memories(content, created_at) VALUES (?, ?)",
            (content, datetime.now(timezone.utc).isoformat()),
        )
    return {"id": cursor.lastrowid, "content": content}


@app.get("/memory")
def list_memory() -> dict[str, Any]:
    with connect_db() as db:
        rows = db.execute(
            "SELECT id, content, created_at FROM memories ORDER BY id DESC LIMIT 100"
        ).fetchall()
    return {"items": [dict(row) for row in rows]}


@app.delete("/memory/{memory_id}")
def delete_memory(memory_id: int) -> dict[str, bool]:
    with connect_db() as db:
        cursor = db.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Memória não encontrada.")
    return {"deleted": True}
