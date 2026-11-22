"""Allowlisted tool execution with observation, bounded retry and explicit recovery."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Callable, Any

@dataclass(frozen=True)
class ToolSpec:
    name: str
    handler: Callable[..., Any]
    idempotent: bool = True
    max_retries: int = 1

class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, ToolSpec] = {}

    def register(self, spec: ToolSpec) -> None:
        if not spec.name or spec.name in self._tools or not callable(spec.handler):
            raise ValueError("Ferramenta inválida ou duplicada.")
        self._tools[spec.name] = spec

    def execute(self, name: str, **kwargs) -> dict:
        spec = self._tools.get(name)
        if spec is None:
            return {"status": "blocked", "tool": name, "error": "Ferramenta fora da lista permitida."}
        attempts = 0
        max_attempts = 1 + (max(0, min(spec.max_retries, 2)) if spec.idempotent else 0)
        while attempts < max_attempts:
            attempts += 1
            try:
                result = spec.handler(**kwargs)
                return {"status": "completed", "tool": name, "attempts": attempts,
                        "observation": result, "recovered": attempts > 1}
            except Exception as exc:
                if attempts >= max_attempts:
                    return {"status": "failed", "tool": name, "attempts": attempts,
                            "error_type": type(exc).__name__, "recovery": "parado sem repetir ação não segura"}
        return {"status": "failed", "tool": name, "attempts": attempts}
