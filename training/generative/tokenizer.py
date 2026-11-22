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


class TrainedBPETokenizer:
    """BPE vocabulary trained from ULTRON's own licensed corpus; no pretrained merges."""
    version = "ultron-bpe-v1"

    def __init__(self, tokenizer_json: str) -> None:
        try:
            from tokenizers import Tokenizer
        except ImportError as exc:
            raise RuntimeError("Install tokenizers to load the trained BPE vocabulary") from exc
        self._tokenizer = Tokenizer.from_file(tokenizer_json)
        self.bos_id = self._tokenizer.token_to_id("[BOS]")
        self.eos_id = self._tokenizer.token_to_id("[EOS]")
        if self.bos_id is None or self.eos_id is None:
            raise ValueError("BPE tokenizer is missing required BOS/EOS tokens")
        self.vocab_size = self._tokenizer.get_vocab_size()

    def encode(self, text: str, *, add_special_tokens: bool = True) -> list[int]:
        values = self._tokenizer.encode(str(text)).ids
        return [self.bos_id, *values, self.eos_id] if add_special_tokens else values

    def decode(self, token_ids: list[int], *, skip_special_tokens: bool = True) -> str:
        values = [int(token) for token in token_ids]
        if skip_special_tokens:
            values = [token for token in values if token not in (self.bos_id, self.eos_id)]
        return self._tokenizer.decode(values, skip_special_tokens=skip_special_tokens)
