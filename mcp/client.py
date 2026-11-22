"""Minimal MCP Streamable HTTP client with persistent session and tool discovery."""
from __future__ import annotations

import json
import os
from typing import Any

import requests


class MCPError(RuntimeError):
    pass


class MCPClient:
    """MCP client for Streamable HTTP endpoints.

    The requests.Session and MCP session id are kept for the lifetime of this
    client. Credentials are read from the environment and never logged.
    """

    def __init__(self, endpoint: str, token: str | None = None, timeout: float = 20.0):
        if not endpoint.startswith("https://"):
            raise ValueError("MCP remoto exige HTTPS.")
        self.endpoint = endpoint
        self.token = token if token is not None else os.getenv("ULTRON_MCP_TOKEN")
        self.timeout = timeout
        self.session = requests.Session()
        self.session_id: str | None = None
        self.protocol_version = "2025-03-26"
        self._request_id = 0
        self.initialized = False

    def _headers(self) -> dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        if self.session_id:
            headers["Mcp-Session-Id"] = self.session_id
        return headers

    @staticmethod
    def _decode_response(response: requests.Response) -> dict[str, Any]:
        response.raise_for_status()
        content_type = response.headers.get("Content-Type", "")
        if "text/event-stream" in content_type:
            payloads = []
            for line in response.text.splitlines():
                if line.startswith("data:"):
                    payloads.append(line[5:].strip())
            for payload in reversed(payloads):
                if payload and payload != "[DONE]":
                    try:
                        parsed = json.loads(payload)
                        if isinstance(parsed, dict) and ("result" in parsed or "error" in parsed):
                            return parsed
                    except json.JSONDecodeError:
                        continue
            raise MCPError("Resposta SSE MCP sem mensagem JSON-RPC.")
        try:
            parsed = response.json()
        except ValueError as exc:
            raise MCPError("Resposta MCP não contém JSON válido.") from exc
        if not isinstance(parsed, dict):
            raise MCPError("Resposta MCP inválida.")
        return parsed

    def _post(self, payload: dict[str, Any], expect_response: bool = True) -> dict[str, Any] | None:
        response = self.session.post(
            self.endpoint,
            json=payload,
            headers=self._headers(),
            timeout=self.timeout,
        )
        new_session = response.headers.get("Mcp-Session-Id")
        if new_session:
            self.session_id = new_session
        if not expect_response and response.status_code in (202, 204):
            response.raise_for_status()
            return None
        message = self._decode_response(response)
        if "error" in message:
            error = message["error"]
            raise MCPError(f"MCP JSON-RPC {error.get('code')}: {error.get('message')}")
        return message

    def _next_id(self) -> int:
        self._request_id += 1
        return self._request_id

    def connect(self) -> dict[str, Any]:
        message = self._post({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "initialize",
            "params": {
                "protocolVersion": self.protocol_version,
                "capabilities": {},
                "clientInfo": {"name": "ULTRON", "version": "1.0"},
            },
        })
        result = (message or {}).get("result", {})
        negotiated = result.get("protocolVersion")
        if negotiated:
            self.protocol_version = negotiated
        self._post({
            "jsonrpc": "2.0",
            "method": "notifications/initialized",
            "params": {},
        }, expect_response=False)
        self.initialized = True
        return result

    def list_tools(self) -> list[dict[str, Any]]:
        if not self.initialized:
            self.connect()
        message = self._post({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/list",
            "params": {},
        })
        tools = (message or {}).get("result", {}).get("tools", [])
        if not isinstance(tools, list):
            raise MCPError("MCP tools/list retornou formato inválido.")
        return tools

    def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.initialized:
            self.connect()
        message = self._post({
            "jsonrpc": "2.0",
            "id": self._next_id(),
            "method": "tools/call",
            "params": {"name": name, "arguments": arguments or {}},
        })
        return (message or {}).get("result", {})

    def close(self) -> None:
        if self.session_id:
            try:
                response = self.session.delete(
                    self.endpoint,
                    headers=self._headers(),
                    timeout=self.timeout,
                )
                if response.status_code not in (200, 202, 204, 404, 405):
                    response.raise_for_status()
            except requests.RequestException:
                # Session termination is optional in MCP; preserve the tool result.
                pass
            finally:
                self.session_id = None
        self.session.close()
        self.initialized = False

    def __enter__(self) -> "MCPClient":
        self.connect()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
