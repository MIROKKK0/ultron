"""Versioned UTF-8 byte tokenizer with two reserved control tokens.

No external vocabulary, pretrained tokenizer, or downloaded model assets.
"""
from __future__ import annotations

TOKENIZER_VERSION = "ultron-byte-v1"
BOS_ID = 256
EOS_ID = 257
VOCAB_SIZE = 258


class ByteTokenizer:
    version = TOKENIZER_VERSION
    vocab_size = VOCAB_SIZE

    def encode(self, text: str, *, add_special_tokens: bool = True) -> list[int]:
        token_ids = list(str(text).encode("utf-8"))
        if add_special_tokens:
            return [BOS_ID, *token_ids, EOS_ID]
        return token_ids

    def decode(self, token_ids: list[int], *, skip_special_tokens: bool = True) -> str:
        values: list[int] = []
        for token_id in token_ids:
            token = int(token_id)
            if token in (BOS_ID, EOS_ID) and skip_special_tokens:
                continue
            if 0 <= token <= 255:
                values.append(token)
        return bytes(values).decode("utf-8", errors="replace")
