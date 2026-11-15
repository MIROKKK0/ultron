"""Optional OpenAI-compatible language provider for ULTRON.

All credentials stay on the server. With no provider configured, ULTRON keeps
using its existing local Qwen/FlyBrain path.
"""
from __future__ import annotations

import os
from typing import Any

import httpx


class ProviderError(RuntimeError):
    """A configured language provider failed or returned an invalid response."""


def provider_configured() -> bool:
    # Gemini is the default free-tier candidate; compatible providers can override it.
    return bool(os.getenv("ULTRON_LLM_API_KEY", "").strip())


def provider_name() -> str | None:
    if not provider_configured():
        return None
    return os.getenv("ULTRON_LLM_NAME", "Gemini 3.8 Flash").strip() or "Gemini 3.8 Flash"


def generate_chat_reply(messages: list[dict[str, str]]) -> str | None:
    """Generate one answer using an OpenAI-compatible chat-completions endpoint.

    Returns None when no provider is configured. Raises ProviderError on
    provider/network/shape failures so callers can fall back transparently.
    """
    if not provider_configured():
        return None

    base_url = os.getenv("ULTRON_LLM_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai").strip().rstrip("/")
    api_key = os.environ["ULTRON_LLM_API_KEY"].strip()
    model = os.getenv("ULTRON_LLM_MODEL", "gemini-3.8-flash").strip()
    if not base_url.startswith("https://"):
        raise ProviderError("O endereço do provedor de IA precisa usar HTTPS.")

    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "temperature": 0.65,
        "max_tokens": 900,
        "stream": False,
    }
    try:
        response = httpx.post(
            f"{base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            json=payload,
            timeout=httpx.Timeout(45.0, connect=10.0),
        )
        response.raise_for_status()
        data = response.json()
    except (httpx.HTTPError, ValueError) as exc:
        raise ProviderError("O provedor de IA online não respondeu corretamente.") from exc

    try:
        content = data["choices"][0]["message"]["content"]
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") for part in content if isinstance(part, dict)
            )
        answer = str(content).strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderError("O provedor retornou uma resposta em formato inválido.") from exc

    if not answer:
        raise ProviderError("O provedor retornou uma resposta vazia.")
    return answer[:16000]
