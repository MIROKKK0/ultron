"""Small decoder-only Transformer initialized entirely from random weights."""
from __future__ import annotations
from dataclasses import asdict, dataclass
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
        if not 1 <= self.heads <= 16 or not 16 <= self.width <= 512 or self.width % self.heads:
            raise ValueError("Width must be 16..512 and divisible by 1..16 heads")
        if not 1 <= self.layers <= 12 or not 0.0 <= self.dropout < 1.0:
            raise ValueError("Invalid layer count or dropout")

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
            nn.Linear(config.width, config.width * 4), nn.GELU(),
            nn.Linear(config.width * 4, config.width), nn.Dropout(config.dropout),
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

    def forward(self, input_ids: torch.Tensor, targets: torch.Tensor | None = None):
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
    def generate(
        self,
        input_ids: torch.Tensor,
        max_new_tokens: int = 64,
        *,
        temperature: float = 0.0,
        top_k: int | None = None,
        generator: torch.Generator | None = None,
    ) -> torch.Tensor:
        """Generate greedily by default, or sample with temperature/top-k."""
        if input_ids.ndim != 2 or input_ids.shape[0] < 1 or input_ids.shape[1] < 1:
            raise ValueError("Generation requires a non-empty [batch, sequence] tensor")
        if temperature < 0:
            raise ValueError("Temperature cannot be negative")
        if top_k is not None and top_k < 1:
            raise ValueError("top_k must be positive when provided")
        was_training = self.training
        try:
            self.eval()
            for _ in range(max(0, min(max_new_tokens, 256))):
                context = input_ids[:, -self.config.context_length:]
                logits, _ = self(context)
                next_logits = logits[:, -1, :]
                if temperature == 0:
                    next_token = torch.argmax(next_logits, dim=-1, keepdim=True)
                else:
                    next_logits = next_logits / temperature
                    if top_k is not None:
                        keep = min(top_k, next_logits.size(-1))
                        threshold = torch.topk(next_logits, keep, dim=-1).values[:, -1, None]
                        next_logits = next_logits.masked_fill(next_logits < threshold, float("-inf"))
                    probabilities = F.softmax(next_logits, dim=-1)
                    next_token = torch.multinomial(probabilities, 1, generator=generator)
                input_ids = torch.cat((input_ids, next_token), dim=1)
            return input_ids
        finally:
            self.train(was_training)

    @torch.no_grad()
    def encode_hidden(self, input_ids: torch.Tensor) -> torch.Tensor:
        """Return final normalized token states for ULTRON-owned local embeddings."""
        if input_ids.ndim != 2 or input_ids.shape[0] < 1 or input_ids.shape[1] < 1:
            raise ValueError("Input IDs must be a non-empty [batch, sequence] tensor")
        _, length = input_ids.shape
        if length > self.config.context_length:
            raise ValueError("Input exceeds configured context")
        was_training = self.training
        try:
            self.eval()
            positions = torch.arange(length, device=input_ids.device)
            hidden = self.token_embedding(input_ids) + self.position_embedding(positions)[None, :, :]
            for block in self.blocks:
                hidden = block(hidden)
            return self.final_norm(hidden)
        finally:
            self.train(was_training)

    def parameter_count(self) -> int:
        return sum(parameter.numel() for parameter in self.parameters())

    def config_dict(self) -> dict:
        return asdict(self.config)
