from __future__ import annotations

import json

import httpx
import pytest

from backend import llm_provider


def configure(monkeypatch):
    monkeypatch.setenv("ULTRON_LLM_BASE_URL", "https://example.ai/v1/")
    monkeypatch.setenv("ULTRON_LLM_API_KEY", "test-secret")
    monkeypatch.setenv("ULTRON_LLM_MODEL", "test-model")


def test_provider_is_optional(monkeypatch):
    for name in ("ULTRON_LLM_BASE_URL", "ULTRON_LLM_API_KEY", "ULTRON_LLM_MODEL"):
        monkeypatch.delenv(name, raising=False)
    assert llm_provider.provider_configured() is False
    assert llm_provider.generate_chat_reply([{"role": "user", "content": "oi"}]) is None


def test_generates_reply_without_exposing_key(monkeypatch):
    configure(monkeypatch)
    captured = {}

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "Olá! Como posso ajudar?"}}]}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["headers"] = kwargs["headers"]
        captured["json"] = kwargs["json"]
        return Response()

    monkeypatch.setattr(llm_provider.httpx, "post", fake_post)
    result = llm_provider.generate_chat_reply([
        {"role": "system", "content": "Você é ULTRON."},
        {"role": "user", "content": "Oi"},
    ])
    assert result == "Olá! Como posso ajudar?"
    assert captured["url"] == "https://example.ai/v1/chat/completions"
    assert captured["headers"]["Authorization"] == "Bearer test-secret"
    assert captured["json"]["model"] == "test-model"
    assert captured["json"]["stream"] is False


def test_rejects_non_https_provider(monkeypatch):
    configure(monkeypatch)
    monkeypatch.setenv("ULTRON_LLM_BASE_URL", "http://example.ai/v1")
    with pytest.raises(llm_provider.ProviderError):
        llm_provider.generate_chat_reply([{"role": "user", "content": "oi"}])


def test_rejects_empty_provider_reply(monkeypatch):
    configure(monkeypatch)

    class Response:
        def raise_for_status(self):
            return None

        def json(self):
            return {"choices": [{"message": {"content": "  "}}]}

    monkeypatch.setattr(llm_provider.httpx, "post", lambda *args, **kwargs: Response())
    with pytest.raises(llm_provider.ProviderError):
        llm_provider.generate_chat_reply([{"role": "user", "content": "oi"}])
