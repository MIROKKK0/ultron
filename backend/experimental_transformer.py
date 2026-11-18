"""Opt-in bridge for ULTRON's experimental decoder-only Transformer."""
from __future__ import annotations
import os, time
from pathlib import Path
from typing import Any

def transformer_status() -> dict[str, Any]:
    enabled = os.getenv("ULTRON_TINY_ENABLED", "false").strip().lower() in {"1", "true", "yes"}
    checkpoint = Path(os.getenv("ULTRON_TINY_CHECKPOINT", "artifacts/ultron-tiny.pt"))
    return {"enabled": enabled, "available": enabled and checkpoint.is_file(),
            "checkpoint_present": checkpoint.is_file(), "checkpoint_path": str(checkpoint),
            "role": "experimental_candidate_only",
            "training_metrics": "validation_loss/perplexity/BPB stored in checkpoint",
            "promotion_policy": "requires held-out dialogue benchmark and human approval"}

def _history_text(history: list[Any] | None) -> list[str]:
    lines = []
    for item in (history or [])[-6:]:
        if isinstance(item, dict):
            role = str(item.get("role", "user")).strip().lower()
            content = str(item.get("content", "")).strip()
            if role in {"user", "assistant"} and content:
                lines.append(f"{role}: {content[:500]}")
        elif isinstance(item, str) and item.strip():
            lines.append(item[:500])
    return lines

def generate_experimental_candidate(prompt: str, *, history: list[Any] | None = None,
                                    memories: list[str] | None = None) -> dict[str, Any]:
    status = transformer_status()
    if not status["enabled"]:
        return {"status": "disabled", **status}
    if not status["available"]:
        return {"status": "checkpoint_missing", **status}
    started = time.perf_counter()
    try:
        import torch
        from training.generative.model import ModelConfig, UltronTinyGPT
        from training.generative.tokenizer import ByteTokenizer, TrainedBPETokenizer
        checkpoint = torch.load(status["checkpoint_path"], map_location="cpu", weights_only=True)
        config_data = checkpoint.get("model_config")
        if not isinstance(config_data, dict):
            raise ValueError("Checkpoint sem configuração.")
        model = UltronTinyGPT(ModelConfig(**config_data))
        model.load_state_dict(checkpoint["model_state"], strict=True)
        version = checkpoint.get("tokenizer_version", "ultron-byte-v1")
        if version == "ultron-bpe-v1":
            tokenizer_path = os.getenv("ULTRON_TINY_TOKENIZER_JSON", "").strip()
            if not tokenizer_path or not Path(tokenizer_path).is_file():
                raise ValueError("Tokenizer BPE não configurado.")
            tokenizer = TrainedBPETokenizer(tokenizer_path)
        elif version == "ultron-byte-v1":
            tokenizer = ByteTokenizer()
        else:
            raise ValueError("Tokenizer incompatível.")
        parts = [f"Memória: {str(x)[:500]}" for x in (memories or [])[:4]]
        parts.extend(_history_text(history))
        parts.append(f"Usuário: {prompt[:1000]}\\nULTRON:")
        encoded = tokenizer.encode("\\n".join(parts))
        # Keep the most recent user turn intact within the model's context.
        ids = torch.tensor([encoded[-model.config.context_length:]], dtype=torch.long)
        limit = max(1, min(int(os.getenv("ULTRON_TINY_MAX_TOKENS", "48")), 96))
        with torch.inference_mode():
            output = model.generate(ids, max_new_tokens=limit, eos_token_id=getattr(tokenizer, "eos_id", 257))
        generated = output[0, ids.shape[1]:].tolist()
        candidate = tokenizer.decode(generated).strip()
        return {"status": "candidate_generated" if candidate else "empty_candidate",
                "candidate": candidate[:3000],
                "metrics": {"latency_ms": round((time.perf_counter()-started)*1000, 2),
                    "generated_tokens": len(generated), "parameter_count": model.parameter_count(),
                    "validation_loss": checkpoint.get("validation_loss"),
                    "validation_perplexity": checkpoint.get("validation_perplexity"),
                    "validation_bits_per_byte": checkpoint.get("validation_bits_per_byte"),
                    "test_loss": checkpoint.get("test_loss"),
                    "test_bits_per_byte": checkpoint.get("test_bits_per_byte"),
                    "training_steps": checkpoint.get("training_steps"),
                    "best_step": checkpoint.get("best_step")},
                "promotion": "blocked_pending_dialogue_benchmarks_and_human_review"}
    except Exception as exc:
        return {"status": "failed", "error": type(exc).__name__,
                "latency_ms": round((time.perf_counter()-started)*1000, 2)}
