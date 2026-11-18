"""Opt-in local generation with ULTRON Tiny; experimental and provider-independent."""
from __future__ import annotations

import os
from pathlib import Path

import torch

from training.generative.model import ModelConfig, UltronTinyGPT
from training.generative.tokenizer import ByteTokenizer, TOKENIZER_VERSION


def build_prompt(message: str, memories: list[str] | None = None,
                 history: list[str] | None = None, *, budget: int = 120) -> str:
    """Build a bounded prompt that reserves the tail for the current user request."""
    if budget < 32:
        raise ValueError("Prompt budget is too small.")
    memory_text = " | ".join(str(item).strip()[:36] for item in (memories or [])[:2])
    history_text = " | ".join(str(item).strip()[:24] for item in (history or [])[-1:])
    prefix = f"ULTRON. Memorias: {memory_text}. Histórico: {history_text}. Pergunta: "
    question_budget = max(24, budget - len(prefix.encode("utf-8")))
    question = str(message).strip()
    encoded_question = question.encode("utf-8")[-question_budget:]
    while encoded_question:
        try:
            question = encoded_question.decode("utf-8")
            break
        except UnicodeDecodeError:
            encoded_question = encoded_question[1:]
    return (prefix + question)[-budget:]


class LocalTransformerRuntime:
    """Loads only an explicitly configured ULTRON checkpoint from local storage."""

    def __init__(self, checkpoint_path: str | None = None) -> None:
        raw = checkpoint_path or os.getenv("ULTRON_GENERATIVE_CHECKPOINT")
        if not raw:
            raise RuntimeError("Configure ULTRON_GENERATIVE_CHECKPOINT para ativar o Transformer local.")
        self.path = Path(raw).expanduser()
        if not self.path.is_file():
            raise RuntimeError("Checkpoint generativo local não encontrado.")
        try:
            checkpoint = torch.load(self.path, map_location="cpu", weights_only=True)
        except Exception as exc:
            raise RuntimeError("Checkpoint generativo inválido.") from exc
        if checkpoint.get("tokenizer_version") != TOKENIZER_VERSION:
            raise ValueError("Checkpoint usa tokenizador incompatível.")
        config = ModelConfig(**checkpoint["model_config"])
        self.model = UltronTinyGPT(config)
        self.model.load_state_dict(checkpoint["model_state"], strict=True)
        self.model.eval()
        self.tokenizer = ByteTokenizer()

    def generate(self, message: str, memories: list[str] | None = None,
                 history: list[str] | None = None, *, max_new_tokens: int = 120) -> str:
        prompt = build_prompt(message, memories, history,
                              budget=min(120, self.model.config.context_length))
        input_ids = self.tokenizer.encode(prompt)
        input_tensor = torch.tensor([input_ids[-self.model.config.context_length:]], dtype=torch.long)
        with torch.inference_mode():
            generated = self.model.generate(input_tensor, max_new_tokens=max_new_tokens, temperature=0.0)
        output = self.tokenizer.decode(generated[0, input_tensor.shape[1]:].tolist()).strip()
        output = "".join(char for char in output if char.isprintable() or char in "\n\t")
        if not output:
            raise RuntimeError("O Transformer local não gerou uma resposta utilizável.")
        return output[:6000]


def generate_local_reply(message: str, memories: list[str] | None = None,
                         history: list[str] | None = None) -> str:
    return LocalTransformerRuntime().generate(message, memories, history)
