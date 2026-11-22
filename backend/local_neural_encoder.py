"""Local embeddings produced by ULTRON's own Tiny Transformer checkpoint.

No hosted API or third-party pretrained weights are used. A trained checkpoint
must be supplied explicitly; otherwise the vector index keeps its transparent
lexical compatibility mode until a neural artifact is available.
"""
from __future__ import annotations

import hashlib
import math
import os
from pathlib import Path
from typing import Any


class LocalNeuralEncoder:
    """Mean-pool ULTRON Tiny hidden states into normalized local embeddings."""

    RETRIEVAL_KIND = "local_ultron_transformer_embedding"

    def __init__(self, checkpoint_path: str | Path | None = None) -> None:
        try:
            import torch
        except ImportError as exc:
            raise RuntimeError("PyTorch é necessário para carregar o encoder neural local.") from exc
        from training.generative.model import ModelConfig, UltronTinyGPT
        from training.generative.tokenizer import ByteTokenizer, TOKENIZER_VERSION

        raw_path = checkpoint_path or os.getenv("ULTRON_NEURAL_EMBEDDINGS_CHECKPOINT")
        if not raw_path:
            raise RuntimeError("Configure ULTRON_NEURAL_EMBEDDINGS_CHECKPOINT com um checkpoint treinado do ULTRON.")
        self.path = Path(raw_path).expanduser()
        if not self.path.is_file():
            raise RuntimeError("Checkpoint neural local não encontrado; não será substituído silenciosamente por outro provedor.")
        self.torch = torch
        try:
            checkpoint = torch.load(self.path, map_location="cpu", weights_only=True)
        except Exception as exc:
            raise RuntimeError("Não foi possível validar o checkpoint neural local.") from exc
        if checkpoint.get("tokenizer_version") != TOKENIZER_VERSION:
            raise ValueError("Checkpoint usa um tokenizador incompatível.")
        config = ModelConfig(**checkpoint["model_config"])
        self.model = UltronTinyGPT(config)
        self.model.load_state_dict(checkpoint["model_state"], strict=True)
        self.model.eval()
        self.tokenizer = ByteTokenizer()
        self.digest = hashlib.sha256(self.path.read_bytes()).hexdigest()
        self.VERSION = f"ultron-tiny-mean-v1:{self.digest[:16]}"

    def encode(self, text: str) -> dict[str, float]:
        normalized = str(text).strip()
        if not normalized:
            return {}
        ids = self.tokenizer.encode(normalized, add_special_tokens=True)
        ids = ids[: self.model.config.context_length]
        if not ids:
            return {}
        tensor = self.torch.tensor([ids], dtype=self.torch.long)
        with self.torch.inference_mode():
            hidden = self.model.encode_hidden(tensor)[0]
            vector = hidden.mean(dim=0).float()
            norm = float(self.torch.linalg.vector_norm(vector).item())
            if not math.isfinite(norm) or norm <= 1e-12:
                return {}
            vector = vector / norm
        return {str(i): round(float(value), 8) for i, value in enumerate(vector.tolist())}
