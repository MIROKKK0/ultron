"""Replaceable model clients; identity, memory and policy remain in ULTRON."""
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
    def from_env(cls):
        name = os.getenv("ULTRON_PROVIDER", "gemini").strip().lower()
        settings = {
            "gemini": ("GEMINI_API_KEY", "GEMINI_MODEL", "GEMINI_BASE_URL",
                       "gemini-2.5-flash", "https://generativelanguage.googleapis.com/v1beta/openai/"),
            "openai": ("OPENAI_API_KEY", "ULTRON_MODEL", "OPENAI_BASE_URL",
                       "gpt-4o-mini", "https://api.openai.com/v1"),
            "openrouter": ("OPENROUTER_API_KEY", "OPENROUTER_MODEL", "OPENROUTER_BASE_URL",
                           "openai/gpt-4o-mini", "https://openrouter.ai/api/v1"),
        }
        if name not in settings:
            raise ValueError(f"Unsupported ULTRON_PROVIDER: {name}")
        key_env, model_env, url_env, default_model, default_url = settings[name]
        key = os.getenv(key_env, "")
        model = os.getenv(model_env, default_model).strip()
        if not key:
            raise ValueError(f"Missing API credential for provider: {name}")
        if not model:
            raise ValueError("Provider model is not configured")
        return cls(name, model, key, os.getenv(url_env, default_url).strip() or None)


def build_provider(config=None):
    cfg = config or ProviderConfig.from_env()
    kwargs = {"api_key": cfg.api_key}
    if cfg.base_url:
        kwargs["base_url"] = cfg.base_url
    return OpenAI(**kwargs), cfg.model
