"""Train ULTRON's own byte-level BPE tokenizer from the training split only."""
from __future__ import annotations
import argparse
from pathlib import Path


def train_tokenizer(corpus_path: str, output_path: str, vocab_size: int = 2048, min_frequency: int = 2) -> dict:
    if vocab_size < 300 or vocab_size > 8192 or min_frequency < 1:
        raise ValueError("vocab_size must be 300..8192 and min_frequency positive")
    try:
        from tokenizers import Tokenizer, decoders, models, pre_tokenizers, trainers
    except ImportError as exc:
        raise RuntimeError("Install tokenizers from requirements-data.txt") from exc
    corpus = Path(corpus_path)
    if not corpus.is_file() or corpus.stat().st_size < 100_000:
        raise ValueError("Training corpus must exist and contain at least 100 KB")
    tokenizer = Tokenizer(models.BPE(unk_token="[UNK]"))
    tokenizer.pre_tokenizer = pre_tokenizers.ByteLevel(add_prefix_space=False)
    tokenizer.decoder = decoders.ByteLevel()
    trainer = trainers.BpeTrainer(
        vocab_size=vocab_size,
        min_frequency=min_frequency,
        special_tokens=["[UNK]", "[BOS]", "[EOS]"],
        initial_alphabet=pre_tokenizers.ByteLevel.alphabet(),
        show_progress=True,
    )
    tokenizer.train([str(corpus)], trainer)
    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    tokenizer.save(str(output))
    return {
        "tokenizer": "ultron-bpe-v1",
        "vocab_size": tokenizer.get_vocab_size(),
        "bos_id": tokenizer.token_to_id("[BOS]"),
        "eos_id": tokenizer.token_to_id("[EOS]"),
        "training_corpus_bytes": corpus.stat().st_size,
        "output": str(output),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", required=True)
    parser.add_argument("--output", default="artifacts/ultron-bpe-tokenizer.json")
    parser.add_argument("--vocab-size", type=int, default=2048)
    parser.add_argument("--min-frequency", type=int, default=2)
    args = parser.parse_args()
    print(train_tokenizer(args.corpus, args.output, args.vocab_size, args.min_frequency))


if __name__ == "__main__":
    main()
