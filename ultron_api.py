"""Small authenticated HTTP API for ULTRON memory and background tasks."""
from __future__ import annotations

import hmac
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Lock, Thread
from urllib.parse import parse_qs, urlparse

from dotenv import load_dotenv
load_dotenv()

from ultron_core import UltronCore, SPECIALISTS


class UltronAPIHandler(BaseHTTPRequestHandler):
    core = UltronCore()

    def _run_chat(self, message: str) -> str:
        with self.server._ultron_chat_lock:
            agent = getattr(self.server, "_ultron_chat_agent", None)
            if agent is None:
                from ultron import Ultron
                agent = Ultron()
                self.server._ultron_chat_agent = agent
            return agent.chat(message)

    def _send_sse(self, payload: dict) -> None:
        body = ("data: " + json.dumps(payload, ensure_ascii=False) + "\\n\\n").encode("utf-8")
        self.wfile.write(body)
        self.wfile.flush()

    def _send(self, status: int, payload: dict) -> None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _authorized(self) -> bool:
        expected = os.getenv("ULTRON_API_TOKEN", "")
        supplied = self.headers.get("Authorization", "")
        if not expected:
            return False
        return hmac.compare_digest(supplied, f"Bearer {expected}")

    def _body(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length < 1 or length > 2_000_000:
            raise ValueError("Corpo ausente ou acima de 2 MB.")
        value = json.loads(self.rfile.read(length))
        if not isinstance(value, dict):
            raise ValueError("O corpo precisa ser um objeto JSON.")
        return value

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/health":
            self._send(200, {"status": "online", "identity": "ULTRON"})
            return
        if not self._authorized():
            self._send(401, {"error": "unauthorized"})
            return
        query = parse_qs(parsed.query)
        if parsed.path == "/api/memory/graph":
            installation_id = (query.get("installation_id") or [""])[0]
            if not installation_id:
                self._send(400, {"error": "installation_id obrigatório"})
                return
            self._send(200, self.core.memory_graph(installation_id=installation_id))
            return
        if parsed.path == "/api/tasks":
            self._send(200, {"tasks": self.core.list_tasks()})
            return
        self._send(404, {"error": "not_found"})

    def do_POST(self) -> None:
        if not self._authorized():
            self._send(401, {"error": "unauthorized"})
            return
        try:
            payload = self._body()
            if self.path in {"/chat", "/chat/stream"}:
                message = str(payload.get("message", "")).strip()
                if not message or len(message) > 12000:
                    self._send(400, {"error": "message inválida"})
                    return
                if self.path == "/chat/stream":
                    self.send_response(200)
                    self.send_header("Content-Type", "text/event-stream; charset=utf-8")
                    self.send_header("Cache-Control", "no-cache")
                    self.send_header("Connection", "keep-alive")
                    self.end_headers()
                    self._send_sse({"type": "stage", "stage": "processing"})
                    reply = self._run_chat(message)
                    self._send_sse({"type": "stage", "stage": "responding"})
                    self._send_sse({"type": "final", "reply": reply, "strategy": "ultron-core"})
                    return
                reply = self._run_chat(message)
                self._send(200, {"reply": reply, "strategy": "ultron-core"})
                return
            if self.path == "/feedback":
                rating = int(payload.get("rating", 0))
                strategy = str(payload.get("strategy", ""))[:120]
                if rating < 1 or rating > 5:
                    self._send(400, {"error": "rating deve estar entre 1 e 5"})
                    return
                self.core.event("chat.feedback", {"rating": rating, "strategy": strategy})
                self._send(200, {"status": "recorded"})
                return
            if self.path == "/api/memory/sync":
                result = self.core.sync_memories(payload.get("installation_id", ""), payload.get("memories", []), replace=bool(payload.get("replace", False)))
                self._send(200, result)
                return
            if self.path == "/api/tasks":
                objective = str(payload.get("objective", "")).strip()
                specialist = str(payload.get("specialist", "architect"))
                if not objective or len(objective) > 12000:
                    self._send(400, {"error": "objective inválido"})
                    return
                if specialist not in SPECIALISTS:
                    self._send(400, {"error": "specialist inválido"})
                    return
                task_id = self.core.create_task(objective, specialist)
                self._send(202, {"task_id": task_id, "status": "queued"})
                return
            self._send(404, {"error": "not_found"})
        except (ValueError, TypeError, json.JSONDecodeError) as exc:
            self._send(400, {"error": str(exc)})
        except Exception as exc:
            self._send(500, {"error": type(exc).__name__})

    def log_message(self, fmt: str, *args) -> None:
        # Avoid recording headers, tokens, message bodies, or memory content.
        print(f"ULTRON API {self.command} {self.path.split('?')[0]}")

    def do_DELETE(self) -> None:
        self._send(405, {"error": "method_not_allowed"})


def main() -> None:
    api_token = os.getenv("ULTRON_API_TOKEN", "")
    if len(api_token) < 32:
        raise SystemExit("Defina ULTRON_API_TOKEN com pelo menos 32 caracteres aleatórios.")
    host = os.getenv("ULTRON_API_HOST", "0.0.0.0")
    port = int(os.getenv("PORT", os.getenv("ULTRON_API_PORT", "8000")))
    server = ThreadingHTTPServer((host, port), UltronAPIHandler)
    server._ultron_chat_lock = Lock()
    if os.getenv("ULTRON_START_WORKER", "0").lower() in {"1", "true", "yes"}:
        if not (os.getenv("ULTRON_LLM_API_KEY") or os.getenv("OPENAI_API_KEY")):
            print("Worker não iniciado: configure ULTRON_LLM_API_KEY ou OPENAI_API_KEY")
        else:
            from scripts.ultron_worker import run_worker
            Thread(target=run_worker, kwargs={"once": False}, daemon=True, name="ultron-agent-worker").start()
            print("ULTRON background worker iniciado no processo da API")
    print(f"ULTRON API online em {host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
