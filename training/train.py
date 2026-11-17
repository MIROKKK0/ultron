"""Reproducible CPU smoke-training for ULTRON's own tiny Transformer.

Example:
  python -m training.train --steps 200 --output artifacts/ultron-tiny.pt
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import torch

from .model import ModelConfig, UltronTinyGPT
from .tokenizer import ByteTokenizer, TOKENIZER_VERSION


def train(args: argparse.Namespace) -> dict:
    torch.manual_seed(args.seed)
    torch.set_num_threads(max(1, min(args.threads, 4)))
    corpus_path = Path(args.corpus)
    corpus = corpus_path.read_text(encoding="utf-8")
    tokenizer = ByteTokenizer()
    encoded = tokenizer.encode(corpus)
    if len(encoded) <= args.context_length + 1:
        raise ValueError("Corpus is too small for the selected context length")

    data = torch.tensor(encoded, dtype=torch.long)
    config = ModelConfig(
        context_length=args.context_length,
        width=args.width,
        layers=args.layers,
        heads=args.heads,
        dropout=0.0,
    )
    model = UltronTinyGPT(config)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)
    model.train()

    for step in range(args.steps):
        starts = torch.randint(0, len(data) - args.context_length - 1, (args.batch_size,))
        inputs = torch.stack([data[i : i + args.context_length] for i in starts])
        targets = torch.stack([data[i + 1 : i + args.context_length + 1] for i in starts])
        _, loss = model(inputs, targets)
        if loss is None:
            raise RuntimeError("Training loss was not produced")
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        if (step + 1) % max(1, args.steps // 10) == 0 or step == 0:
            print(json.dumps({"step": step + 1, "loss": round(float(loss.item()), 5)}))

    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    torch.save(
        {
            "model_state": model.state_dict(),
            "model_config": model.config_dict(),
            "tokenizer_version": TOKENIZER_VERSION,
            "corpus_sha256": hashlib.sha256(corpus.encode("utf-8")).hexdigest(),
            "training_steps": args.steps,
            "parameter_count": model.parameter_count(),
            "experimental": True,
        },
        output,
    )
    return {
        "checkpoint": str(output),
        "parameters": model.parameter_count(),
        "training_steps": args.steps,
        "tokenizer": TOKENIZER_VERSION,
        "warning": "Experimental tiny model; not a production assistant or ChatGPT-equivalent.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", default="training/corpus_pt.txt")
    parser.add_argument("--output", default="artifacts/ultron-tiny.pt")
    parser.add_argument("--steps", type=int, default=1000)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--context-length", type=int, default=128)
    parser.add_argument("--width", type=int, default=64)
    parser.add_argument("--layers", type=int, default=2)
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()
    if args.steps < 1 or args.batch_size < 1:
        parser.error("--steps and --batch-size must be positive")
    print(json.dumps(train(args), ensure_ascii=False))


if __name__ == "__main__":
    main()
