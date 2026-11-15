"""Hosted language generation with free-tier provider fallback.

FlyBrain is always executed by the chat endpoint before this module is called.
This module only turns the already-produced neural control signals into language.
It never stores prompts, logs credentials, or silently selects paid models.
"""
from __future__ import annotations

import os
import time
from typing import Any

import httpx


_PROVIDER_DEFAULTS = {
    "groq": {
        "key_env": "GROQ_API_KEY",
        "base_env": "GROQ_BASE_URL",
        "model_env": "GROQ_MODEL",
        "base_url": "https://api.groq.com/openai/v1",
        "model": "openai/gpt-oss-20b",
    },
    "openrouter": {
        "key_env": "OPENROUTER_API_KEY",
        "base_env": "OPENROUTER_BASE_URL",
        "model_env": "OPENROUTER_MODEL",
        "base_url": "https://openrouter.ai/api/v1",
        "model": "openrouter/free",
    },
}


def configured_providers() -> list[str]:
    """Return configured provider names only; never expose keys or values."""
    order = os.getenv("ULTRON_AI_PROVIDER_ORDER", "groq,openrouter")
    names: list[str] = []
    for raw_name in order.split(","):
        name = raw_name.strip().lower()
        config = _PROVIDER_DEFAULTS.get(name)
        if config and os.getenv(config["key_env"], "").strip():
            names.append(name)
    return names


def _neural_summary(state: dict[str, Any]) -> str:
    roles = state.get("role_scores", {})
    if not isinstance(roles, dict):
        roles = {}
    safe_roles = {
        name: round(float(roles.get(name, 0.0)), 4)
        for name in ("planner", "solver", "critic")
    }
    activity = state.get("group_activity", {})
    if not isinstance(activity, dict):
        activity = {}
    safe_activity = {
        str(name)[:40]: round(float(value), 4)
        for name, value in list(activity.items())[:8]
        if isinstance(value, (int, float))
    }
    return (
        f"Núcleo: {str(state.get('core', 'FlyBrain'))[:80]}; "
        f"runtime: {str(state.get('runtime', 'local'))[:80]}; "
        f"prioridades: {safe_roles}; atividade: {safe_activity}."
    )


def generate_reply(
    message: str,
    neural_state: dict[str, Any],
    research_context: str | None = None,
) -> dict[str, Any] | None:
    """Try configured free-tier providers in order; return None for local fallback.

    Provider order is explicit and only includes Groq and OpenRouter free routing.
    Each request is bounded by a short timeout and a small output budget.
    """
    providers = configured_providers()
    if not providers:
        return None

    system_prompt = (
        "Você é a camada de linguagem do ULTRON. O FlyBrain já processou a mensagem "
        "e permanece o núcleo obrigatório; não o substitua nem afirme que ele gerou "
        "o texto. Responda em português brasileiro natural, com clareza e sem frases "
        "repetitivas de processamento. Não invente ações, memória, fontes ou resultados. "
        "Se houver contexto de pesquisa, use somente os fatos e URLs presentes nele; "
        "diferencie incerteza de fato e preserve os links relevantes. "
        "Sinais de controle do FlyBrain: " + _neural_summary(neural_state)
    )
    user_content = message.strip()
    if research_context:
        user_content += (
            "\n\nCONTEXTO DE PESQUISA COM FONTES (trate como evidência limitada):\n"
            + research_context[:10000]
        )

    for provider in providers:
        config = _PROVIDER_DEFAULTS[provider]
        api_key = os.getenv(config["key_env"], "").strip()
        base_url = os.getenv(config["base_env"], config["base_url"]).strip().rstrip("/")
        model = os.getenv(config["model_env"], config["model"]).strip()
        if not api_key or not base_url.startswith("https://") or not model:
            continue

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        if provider == "openrouter":
            headers["X-Title"] = "ULTRON"
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content},
            ],
            "temperature": 0.3,
            "max_tokens": 700,
            "stream": False,
        }

        started = time.perf_counter()
        try:
            with httpx.Client(timeout=httpx.Timeout(9.0, connect=3.0)) as client:
                response = client.post(
                    f"{base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                )
            if response.status_code < 200 or response.status_code >= 300:
                # Rate limits, temporary outages and bad provider configuration
                # move to the next explicitly configured free-tier provider.
                continue
            data = response.json()
            choices = data.get("choices", [])
            content = (
                choices[0].get("message", {}).get("content")
                if choices and isinstance(choices[0], dict)
                else None
            )
            if not isinstance(content, str) or not content.strip():
                continue
            return {
                "text": content.strip(),
                "provider": provider,
                "model": model,
                "latency_ms": round((time.perf_counter() - started) * 1000.0, 2),
            }
        except (httpx.HTTPError, ValueError, KeyError, TypeError):
            # No exception details are returned to public clients; the next
            # provider is tried and the caller can fall back to local decoding.
            continue
    return None
