"""Small decoder-only Transformer initialized entirely from random weights."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math

import torch
from torch import nn
from torch.nn import functional as F

from .tokenizer import VOCAB_SIZE


@dataclass(frozen=True)
class ModelConfig:
    vocab_size: int = VOCAB_SIZE
    context_length: int = 128
    width: int = 64
    layers: int = 2
    heads: int = 4
    dropout: float = 0.0

    def validate(self) -> None:
        if self.vocab_size < VOCAB_SIZE:
            raise ValueError("Vocabulary cannot be smaller than the byte tokenizer")
        if not 8 <= self.context_length <= 2048:
            raise ValueError("Context length must be between 8 and 2048")
        if not 16 <= self.width <= 512 or self.width % self.heads:
            raise ValueError("Width must be 16..512 and divisible by the number of heads")
        if not 1 <= self.layers <= 12 or not 1 <= self.heads <= 16:
            raise ValueError("Layers or attention heads exceed the safe experiment budget")
        if not 0.0 <= self.dropout < 1.0:
            raise ValueError("Dropout must be in [0, 1)")


class CausalSelfAttention(nn.Module):
    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        self.heads = config.heads
        self.head_width = config.width // config.heads
        self.qkv = nn.Linear(config.width, config.width * 3, bias=False)
        self.projection = nn.Linear(config.width, config.width, bias=False)
        self.dropout = nn.Dropout(config.dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        batch, length, width = x.shape
        q, k, v = self.qkv(x).chunk(3, dim=-1)
        shape = (batch, length, self.heads, self.head_width)
        q, k, v = (part.view(shape).transpose(1, 2) for part in (q, k, v))

        # PyTorch's fused scaled-dot-product attention avoids allocating an
        # explicit LxL causal mask and selects an optimized backend when possible.
        attended = F.scaled_dot_product_attention(
            q, k, v,
            dropout_p=self.dropout.p if self.training else 0.0,
            is_causal=True,
        )
        attended = attended.transpose(1, 2).contiguous().view(batch, length, width)
        return self.projection(attended)


class TransformerBlock(nn.Module):
    def __init__(self, config: ModelConfig) -> None:
        super().__init__()
        self.norm_attention = nn.LayerNorm(config.width)
        self.attention = CausalSelfAttention(config)
        self.norm_mlp = nn.LayerNorm(config.width)
        self.mlp = nn.Sequential(
            nn.Linear(config.width, config.width * 4),
            nn.GELU(),
            nn.Linear(config.width * 4, config.width),
            nn.Dropout(config.dropout),
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = x + self.attention(self.norm_attention(x))
        return x + self.mlp(self.norm_mlp(x))


class UltronTinyGPT(nn.Module):
    def __init__(self, config: ModelConfig | None = None) -> None:
        super().__init__()
        self.config = config or ModelConfig()
        self.config.validate()
        self.token_embedding = nn.Embedding(self.config.vocab_size, self.config.width)
        self.position_embedding = nn.Embedding(self.config.context_length, self.config.width)
        self.blocks = nn.ModuleList(TransformerBlock(self.config) for _ in range(self.config.layers))
        self.final_norm = nn.LayerNorm(self.config.width)
        self.language_head = nn.Linear(self.config.width, self.config.vocab_size, bias=False)
        self.language_head.weight = self.token_embedding.weight

    def forward(
        self, input_ids: torch.Tensor, targets: torch.Tensor | None = None
    ) -> tuple[torch.Tensor, torch.Tensor | None]:
        if input_ids.ndim != 2 or input_ids.shape[0] < 1 or input_ids.shape[1] < 1:
            raise ValueError("Input IDs must be a non-empty [batch, sequence] tensor")
        _, length = input_ids.shape
        if length > self.config.context_length:
            raise ValueError("Input exceeds configured context length")
        positions = torch.arange(length, device=input_ids.device)
        x = self.token_embedding(input_ids) + self.position_embedding(positions)[None, :, :]
        for block in self.blocks:
            x = block(x)
        logits = self.language_head(self.final_norm(x))
        loss = None
        if targets is not None:
            if targets.shape != input_ids.shape:
                raise ValueError("Targets must have the same shape as input IDs")
            loss = F.cross_entropy(logits.reshape(-1, logits.size(-1)), targets.reshape(-1))
        return logits, loss

    @torch.no_grad()
    def generate(self, input_ids: torch.Tensor, max_new_tokens: int = 64) -> torch.Tensor:
        if input_ids.ndim != 2 or input_ids.shape[0] < 1 or input_ids.shape[1] < 1:
            raise ValueError("Generation requires a non-empty [batch, sequence] tensor")
        was_training = self.training
        try:
            self.eval()
            for _ in range(max(0, min(max_new_tokens, 256))):
                context = input_ids[:, -self.config.context_length :]
                logits, _ = self(context)
                next_token = torch.argmax(logits[:, -1, :], dim=-1, keepdim=True)
                input_ids = torch.cat((input_ids, next_token), dim=1)
            return input_ids
        finally:
            self.train(was_training)

    def parameter_count(self) -> int:
        return sum(parameter.numel() for parameter in self.parameters())

    def config_dict(self) -> dict:
        return asdict(self.config)
