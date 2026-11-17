"""Versioned UTF-8 byte tokenizer; no external vocabulary or pretrained assets."""
from __future__ import annotations

TOKENIZER_VERSION = "ultron-byte-v1"
BOS_ID = 256
EOS_ID = 257
VOCAB_SIZE = 258


class ByteTokenizer:
    version = TOKENIZER_VERSION
    vocab_size = VOCAB_SIZE

    def encode(self, text: str, *, add_special_tokens: bool = True) -> list[int]:
        values = list(str(text).encode("utf-8"))
        return [BOS_ID, *values, EOS_ID] if add_special_tokens else values

    def decode(self, token_ids: list[int], *, skip_special_tokens: bool = True) -> str:
        output: list[int] = []
        for raw in token_ids:
            token = int(raw)
            if token in (BOS_ID, EOS_ID):
                if skip_special_tokens:
                    continue
                raise ValueError("Control tokens are not UTF-8 bytes")
            if 0 <= token <= 255:
                output.append(token)
        return bytes(output).decode("utf-8", errors="replace")
