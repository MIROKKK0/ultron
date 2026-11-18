"""Replaceable model adapters; identity and memory stay outside providers."""

from dataclasses import dataclass
import os
from typing import Optional

from openai import OpenAI


@dataclass(frozen=True)
class ProviderConfig:
    name: str
    model: str
    api_key: str
    base_url: Optional[str] = None

    @classmethod
    def from_env(cls) -> "ProviderConfig":
        name = os.getenv("ULTRON_PROVIDER", "openai").strip().lower()
        if name == "gemini":
            key = os.getenv("GEMINI_API_KEY", "")
            base = os.getenv("GEMINI_BASE_URL", "https://generativelanguage.googleapis.com/v1beta/openai/")
            model = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
        elif name == "openrouter":
            key = os.getenv("OPENROUTER_API_KEY", "")
            base = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
            model = os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini")
        elif name == "openai":
            key = os.getenv("OPENAI_API_KEY", "")
            base = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
            model = os.getenv("ULTRON_MODEL", "gpt-4o-mini")
        else:
            key = os.getenv("ULTRON_API_KEY", "")
            base = os.getenv("ULTRON_BASE_URL", "") or None
            model = os.getenv("ULTRON_MODEL", "")
        if not key:
            raise ValueError(f"Chave de API ausente para o provedor '{name}'.")
        if not model:
            raise ValueError("Modelo não configurado para o provedor selecionado.")
        return cls(name=name, model=model, api_key=key, base_url=base)


def build_provider(config: Optional[ProviderConfig] = None):
    """Return an OpenAI-compatible client and model without owning core state."""
    cfg = config or ProviderConfig.from_env()
    kwargs = {"api_key": cfg.api_key}
    if cfg.base_url:
        kwargs["base_url"] = cfg.base_url
    return OpenAI(**kwargs), cfg.model
