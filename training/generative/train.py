"""Reproducible CPU training and held-out evaluation for ULTRON Tiny."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path

import torch

from .model import ModelConfig, UltronTinyGPT
from .tokenizer import ByteTokenizer, TOKENIZER_VERSION


def split_corpus(data: torch.Tensor, context_length: int, validation_fraction: float = 0.1):
    """Split sequentially before sampling windows, preventing train/validation overlap."""
    if not 0.05 <= validation_fraction <= 0.4:
        raise ValueError("Validation fraction must be between 0.05 and 0.40")
    split_at = int(len(data) * (1.0 - validation_fraction))
    if split_at <= context_length + 1 or len(data) - split_at <= context_length + 1:
        raise ValueError("Corpus must contain enough tokens for both train and validation")
    return data[:split_at], data[split_at:]


@torch.no_grad()
def evaluate_loss(
    model: UltronTinyGPT,
    data: torch.Tensor,
    *,
    batch_size: int,
    batches: int,
    context_length: int,
    seed: int,
) -> float:
    """Estimate next-token loss on held-out windows without changing model mode."""
    if len(data) <= context_length + 1 or batch_size < 1 or batches < 1:
        raise ValueError("Insufficient evaluation data or invalid batch settings")
    was_training = model.training
    generator = torch.Generator(device="cpu").manual_seed(seed)
    losses = []
    try:
        model.eval()
        for _ in range(batches):
            starts = torch.randint(
                0, len(data) - context_length - 1, (batch_size,), generator=generator
            )
            inputs = torch.stack([data[int(i) : int(i) + context_length] for i in starts])
            targets = torch.stack([data[int(i) + 1 : int(i) + context_length + 1] for i in starts])
            _, loss = model(inputs, targets)
            if loss is None:
                raise RuntimeError("Evaluation loss was not produced")
            losses.append(float(loss.item()))
        return sum(losses) / len(losses)
    finally:
        model.train(was_training)


def train(args: argparse.Namespace) -> dict:
    if args.steps < 1 or args.batch_size < 1 or args.eval_batches < 1:
        raise ValueError("Steps, batch size and evaluation batches must be positive")
    if args.eval_interval < 1 or not 1 <= args.threads <= 4:
        raise ValueError("Evaluation interval must be positive and threads must be 1..4")

    torch.manual_seed(args.seed)
    torch.set_num_threads(args.threads)
    corpus_path = Path(args.corpus)
    corpus = corpus_path.read_text(encoding="utf-8")
    encoded = ByteTokenizer().encode(corpus)
    data = torch.tensor(encoded, dtype=torch.long)
    train_data, validation_data = split_corpus(
        data, args.context_length, args.validation_fraction
    )

    config = ModelConfig(
        context_length=args.context_length,
        width=args.width,
        layers=args.layers,
        heads=args.heads,
    )
    model = UltronTinyGPT(config)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)
    model.train()

    for step in range(args.steps):
        starts = torch.randint(0, len(train_data) - args.context_length - 1, (args.batch_size,))
        inputs = torch.stack([train_data[int(i) : int(i) + args.context_length] for i in starts])
        targets = torch.stack([train_data[int(i) + 1 : int(i) + args.context_length + 1] for i in starts])
        _, loss = model(inputs, targets)
        if loss is None:
            raise RuntimeError("Training loss was not produced")
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()

        if step == 0 or (step + 1) % args.eval_interval == 0 or step + 1 == args.steps:
            validation_loss = evaluate_loss(
                model, validation_data,
                batch_size=args.batch_size,
                batches=args.eval_batches,
                context_length=args.context_length,
                seed=args.seed + step + 1,
            )
            print(json.dumps({
                "step": step + 1,
                "train_loss": round(float(loss.item()), 5),
                "validation_loss": round(validation_loss, 5),
                "validation_perplexity": round(math.exp(min(validation_loss, 80)), 5),
            }))

    final_validation_loss = evaluate_loss(
        model, validation_data,
        batch_size=args.batch_size,
        batches=max(args.eval_batches, 10),
        context_length=args.context_length,
        seed=args.seed + args.steps + 1,
    )
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary_output = output.with_name(output.name + ".tmp")
    torch.save(
        {
            "model_state": model.state_dict(),
            "model_config": model.config_dict(),
            "tokenizer_version": TOKENIZER_VERSION,
            "corpus_sha256": hashlib.sha256(corpus.encode("utf-8")).hexdigest(),
            "training_steps": args.steps,
            "seed": args.seed,
            "validation_fraction": args.validation_fraction,
            "validation_loss": final_validation_loss,
            "validation_perplexity": math.exp(min(final_validation_loss, 80)),
            "parameter_count": model.parameter_count(),
            "experimental": True,
        },
        temporary_output,
    )
    temporary_output.replace(output)
    return {
        "checkpoint": str(output),
        "parameters": model.parameter_count(),
        "training_steps": args.steps,
        "tokenizer": TOKENIZER_VERSION,
        "validation_loss": round(final_validation_loss, 5),
        "validation_perplexity": round(math.exp(min(final_validation_loss, 80)), 5),
        "warning": "Experimental model only; not a production assistant or ChatGPT-equivalent.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", default="training/generative/corpus_pt.txt")
    parser.add_argument("--output", default="artifacts/ultron-tiny.pt")
    parser.add_argument("--steps", type=int, default=1000)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--context-length", type=int, default=128)
    parser.add_argument("--width", type=int, default=64)
    parser.add_argument("--layers", type=int, default=2)
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--validation-fraction", type=float, default=0.1)
    parser.add_argument("--eval-interval", type=int, default=100)
    parser.add_argument("--eval-batches", type=int, default=10)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()
    try:
        print(json.dumps(train(args), ensure_ascii=False))
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
