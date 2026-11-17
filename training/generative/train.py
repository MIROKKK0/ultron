"""Reproducible CPU training and held-out evaluation for ULTRON Tiny."""
from __future__ import annotations
import argparse, hashlib, json, math
from pathlib import Path
import torch
from .model import ModelConfig, UltronTinyGPT
from .tokenizer import ByteTokenizer, TrainedBPETokenizer

def sample_batch(data: torch.Tensor, batch_size: int, context_length: int, *, generator=None):
    """Vectorized next-token windows; avoids Python slicing/stacking per sample."""
    if batch_size < 1 or context_length < 1 or len(data) <= context_length:
        raise ValueError("Insufficient data or invalid batch dimensions")
    starts = torch.randint(0, len(data) - context_length, (batch_size,), generator=generator)
    offsets = torch.arange(context_length)
    indices = starts[:, None] + offsets[None, :]
    return data[indices], data[indices + 1]


def split_corpus(data: torch.Tensor, context_length: int, validation_fraction: float = 0.1):
    """Split sequentially before sampling windows, preventing train/validation overlap."""
    if not 0.05 <= validation_fraction <= 0.4:
        raise ValueError("Validation fraction must be between 0.05 and 0.40")
    split_at = int(len(data) * (1.0 - validation_fraction))
    if split_at <= context_length + 1 or len(data) - split_at <= context_length + 1:
        raise ValueError("Corpus must contain enough tokens for both train and validation")
    return data[:split_at], data[split_at:]

@torch.no_grad()
def evaluate_loss(model, data, *, batch_size: int, batches: int, context_length: int, seed: int) -> float:
    """Estimate next-token loss on held-out windows without changing model mode."""
    if len(data) <= context_length + 1 or batch_size < 1 or batches < 1:
        raise ValueError("Insufficient evaluation data or invalid batch settings")
    was_training = model.training
    generator = torch.Generator(device="cpu").manual_seed(seed)
    losses = []
    try:
        model.eval()
        for _ in range(batches):
            inputs, targets = sample_batch(data, batch_size, context_length, generator=generator)
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
    if args.warmup_steps < 0 or not 0.0 < args.min_lr_ratio <= 1.0:
        raise ValueError("Warmup must be non-negative and min LR ratio must be in (0, 1]")
    if args.early_stopping_patience < 0 or args.min_delta < 0:
        raise ValueError("Early stopping patience and min_delta must be non-negative")
    torch.manual_seed(args.seed)
    torch.set_num_threads(args.threads)
    corpus = Path(args.corpus).read_text(encoding="utf-8")
    tokenizer_json_path = getattr(args, "tokenizer_json", None)
    tokenizer = TrainedBPETokenizer(tokenizer_json_path) if tokenizer_json_path else ByteTokenizer()
    data = torch.tensor(tokenizer.encode(corpus), dtype=torch.long)
    if args.validation_corpus:
        train_data = data
        validation_text = Path(args.validation_corpus).read_text(encoding="utf-8")
        validation_data = torch.tensor(tokenizer.encode(validation_text), dtype=torch.long)
    else:
        train_data, validation_data = split_corpus(data, args.context_length, args.validation_fraction)
        validation_text = ""
    test_text = Path(args.test_corpus).read_text(encoding="utf-8") if args.test_corpus else ""
    test_data = torch.tensor(tokenizer.encode(test_text), dtype=torch.long) if test_text else None
    if len(validation_data) <= args.context_length + 1:
        raise ValueError("Validation corpus is too short for the configured context")
    if test_data is not None and len(test_data) <= args.context_length + 1:
        raise ValueError("Test corpus is too short for the configured context")
    config = ModelConfig(vocab_size=tokenizer.vocab_size, context_length=args.context_length, width=args.width, layers=args.layers, heads=args.heads)
    model = UltronTinyGPT(config)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)
    sampler = torch.Generator(device="cpu").manual_seed(args.seed + 1)
    warmup_steps = min(args.warmup_steps, max(0, args.steps - 1))
    def learning_rate_scale(step: int) -> float:
        if warmup_steps and step < warmup_steps:
            return (step + 1) / warmup_steps
        progress = (step - warmup_steps) / max(1, args.steps - warmup_steps)
        cosine = 0.5 * (1.0 + math.cos(math.pi * min(1.0, progress)))
        return args.min_lr_ratio + (1.0 - args.min_lr_ratio) * cosine
    scheduler = torch.optim.lr_scheduler.LambdaLR(optimizer, learning_rate_scale)
    model.train()
    best_validation_loss = float("inf")
    best_step = 0
    best_state = None
    stale_evaluations = 0
    completed_steps = 0
    for step in range(args.steps):
        inputs, targets = sample_batch(train_data, args.batch_size, args.context_length, generator=sampler)
        _, loss = model(inputs, targets)
        if loss is None:
            raise RuntimeError("Training loss was not produced")
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        scheduler.step()
        completed_steps = step + 1
        if step == 0 or completed_steps % args.eval_interval == 0 or completed_steps == args.steps:
            val_loss = evaluate_loss(model, validation_data, batch_size=args.batch_size,
                batches=args.eval_batches, context_length=args.context_length, seed=args.seed + completed_steps)
            improved = val_loss < best_validation_loss - args.min_delta
            if improved:
                best_validation_loss = val_loss
                best_step = completed_steps
                best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
                stale_evaluations = 0
            else:
                stale_evaluations += 1
            print(json.dumps({"step": completed_steps, "train_loss": round(float(loss.item()), 5),
                "learning_rate": round(optimizer.param_groups[0]["lr"], 8),
                "validation_loss": round(val_loss, 5),
                "best_validation_loss": round(best_validation_loss, 5),
                "best_step": best_step,
                "validation_perplexity": round(math.exp(min(val_loss, 80)), 5)}))
            if args.early_stopping_patience and stale_evaluations >= args.early_stopping_patience:
                print(json.dumps({"early_stopping": True, "step": completed_steps,
                    "patience": args.early_stopping_patience, "best_step": best_step}))
                break
    if best_state is not None:
        model.load_state_dict(best_state)
    final_loss = evaluate_loss(model, validation_data, batch_size=args.batch_size,
        batches=max(args.eval_batches, 10), context_length=args.context_length, seed=args.seed + completed_steps + 1)
    test_loss = evaluate_loss(model, test_data, batch_size=args.batch_size,
        batches=max(args.eval_batches, 10), context_length=args.context_length, seed=args.seed + completed_steps + 2) if test_data is not None else None
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_name(output.name + ".tmp")
    torch.save({"model_state": model.state_dict(), "model_config": model.config_dict(),
        "tokenizer_version": tokenizer.version, "tokenizer_vocab_size": tokenizer.vocab_size,
        "tokenizer_json_sha256": hashlib.sha256(Path(tokenizer_json_path).read_bytes()).hexdigest() if tokenizer_json_path else None, "corpus_sha256": hashlib.sha256(corpus.encode("utf-8")).hexdigest(),
        "training_steps": completed_steps, "requested_training_steps": args.steps,
        "best_step": best_step, "best_validation_loss": best_validation_loss,
        "early_stopping_patience": args.early_stopping_patience, "min_delta": args.min_delta,
        "seed": args.seed, "validation_fraction": args.validation_fraction,
        "corpus_characters": len(corpus), "validation_corpus_sha256": hashlib.sha256(validation_text.encode("utf-8")).hexdigest() if validation_text else None,
        "test_corpus_sha256": hashlib.sha256(test_text.encode("utf-8")).hexdigest() if test_text else None,
        "test_loss": test_loss, "learning_rate": args.learning_rate,
        "warmup_steps": warmup_steps, "min_lr_ratio": args.min_lr_ratio,
        "validation_loss": final_loss, "validation_perplexity": math.exp(min(final_loss, 80)),
        "parameter_count": model.parameter_count(), "experimental": True}, temp)
    temp.replace(output)
    return {"checkpoint": str(output), "parameters": model.parameter_count(), "training_steps": completed_steps,
        "requested_training_steps": args.steps, "best_step": best_step,
        "tokenizer": tokenizer.version, "validation_loss": round(final_loss, 5),
        "validation_perplexity": round(math.exp(min(final_loss, 80)), 5),
        "test_loss": round(test_loss, 5) if test_loss is not None else None,
        "warning": "Experimental model only; not a production assistant or ChatGPT-equivalent."}

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--corpus", default="training/generative/corpus_pt.txt")
    parser.add_argument("--validation-corpus", default=None)
    parser.add_argument("--test-corpus", default=None)
    parser.add_argument("--output", default="artifacts/ultron-tiny.pt")
    parser.add_argument("--tokenizer-json", default=None)
    parser.add_argument("--steps", type=int, default=1000)
    parser.add_argument("--batch-size", type=int, default=8)
    parser.add_argument("--context-length", type=int, default=128)
    parser.add_argument("--width", type=int, default=64)
    parser.add_argument("--layers", type=int, default=2)
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--learning-rate", type=float, default=3e-4)
    parser.add_argument("--warmup-steps", type=int, default=50)
    parser.add_argument("--min-lr-ratio", type=float, default=0.1)
    parser.add_argument("--validation-fraction", type=float, default=0.1)
    parser.add_argument("--eval-interval", type=int, default=100)
    parser.add_argument("--eval-batches", type=int, default=10)
    parser.add_argument("--early-stopping-patience", type=int, default=8)
    parser.add_argument("--min-delta", type=float, default=0.0005)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()
    try:
        print(json.dumps(train(args), ensure_ascii=False))
    except (ValueError, OSError) as exc:
        parser.error(str(exc))

if __name__ == "__main__":
    main()
