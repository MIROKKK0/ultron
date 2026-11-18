"""Contrastive fine-tuning and held-out retrieval evaluation for ULTRON's local encoder.

Input JSONL rows contain {"query": "...", "positive": "..."}.
The evaluation file must be held out from training. No external model or API is used.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from pathlib import Path

import torch
import torch.nn.functional as F

from training.generative.model import ModelConfig, UltronTinyGPT
from training.generative.tokenizer import ByteTokenizer, TOKENIZER_VERSION


def load_pairs(path: str) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for line_number, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        item = json.loads(line)
        query, positive = str(item.get("query", "")).strip(), str(item.get("positive", "")).strip()
        if not query or not positive:
            raise ValueError(f"Par de treino inválido na linha {line_number}")
        pairs.append((query[:1000], positive[:1000]))
    if len(pairs) < 8:
        raise ValueError("São necessários pelo menos oito pares contrastivos.")
    return pairs


def encode_batch(model: UltronTinyGPT, tokenizer: ByteTokenizer, texts: list[str], device: torch.device) -> torch.Tensor:
    encoded = [tokenizer.encode(text)[: model.config.context_length] for text in texts]
    width = max(len(row) for row in encoded)
    ids = torch.zeros((len(encoded), width), dtype=torch.long, device=device)
    mask = torch.zeros((len(encoded), width), dtype=torch.bool, device=device)
    for index, row in enumerate(encoded):
        ids[index, :len(row)] = torch.tensor(row, dtype=torch.long, device=device)
        mask[index, :len(row)] = True
    hidden = model.encode_hidden(ids)
    pooled = (hidden * mask.unsqueeze(-1)).sum(dim=1) / mask.sum(dim=1, keepdim=True).clamp_min(1)
    return F.normalize(pooled, dim=-1)


@torch.no_grad()
def retrieval_metrics(model: UltronTinyGPT, tokenizer: ByteTokenizer,
                      pairs: list[tuple[str, str]], device: torch.device) -> dict:
    model.eval()
    queries = encode_batch(model, tokenizer, [q for q, _ in pairs], device)
    candidates = encode_batch(model, tokenizer, [p for _, p in pairs], device)
    scores = queries @ candidates.T
    ranks = []
    for index in range(len(pairs)):
        order = torch.argsort(scores[index], descending=True).tolist()
        ranks.append(order.index(index) + 1)
    return {
        "queries": len(pairs),
        "recall_at_1": round(sum(rank == 1 for rank in ranks) / len(ranks), 4),
        "recall_at_5": round(sum(rank <= 5 for rank in ranks) / len(ranks), 4),
        "mean_reciprocal_rank": round(sum(1.0 / rank for rank in ranks) / len(ranks), 4),
        "median_rank": sorted(ranks)[len(ranks) // 2],
    }


def train(args: argparse.Namespace) -> dict:
    if args.steps < 1 or args.batch_size < 4 or args.temperature <= 0 or args.learning_rate <= 0:
        raise ValueError("Hiperparâmetros contrastivos inválidos.")
    train_pairs, eval_pairs = load_pairs(args.train_pairs), load_pairs(args.eval_pairs)
    train_hash = hashlib.sha256(Path(args.train_pairs).read_bytes()).hexdigest()
    eval_hash = hashlib.sha256(Path(args.eval_pairs).read_bytes()).hexdigest()
    if train_hash == eval_hash:
        raise ValueError("Treino e avaliação precisam ser arquivos distintos.")
    random.seed(args.seed)
    torch.manual_seed(args.seed)
    torch.set_num_threads(max(1, min(args.threads, 4)))
    device = torch.device("cpu")
    tokenizer = ByteTokenizer()
    config = ModelConfig(context_length=args.context_length, width=args.width,
                         layers=args.layers, heads=args.heads)
    model = UltronTinyGPT(config).to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate)
    before = retrieval_metrics(model, tokenizer, eval_pairs, device)
    generator = random.Random(args.seed)
    best_state = None
    best_mrr = -1.0
    for step in range(1, args.steps + 1):
        batch = [train_pairs[index] for index in generator.sample(range(len(train_pairs)), min(args.batch_size, len(train_pairs)))]
        queries = encode_batch(model, tokenizer, [item[0] for item in batch], device)
        positives = encode_batch(model, tokenizer, [item[1] for item in batch], device)
        logits = (queries @ positives.T) / args.temperature
        labels = torch.arange(len(batch), device=device)
        loss = (F.cross_entropy(logits, labels) + F.cross_entropy(logits.T, labels)) / 2
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        optimizer.step()
        if step % args.eval_interval == 0 or step == args.steps:
            metrics = retrieval_metrics(model, tokenizer, eval_pairs, device)
            print(json.dumps({"step": step, "contrastive_loss": round(float(loss.item()), 5), **metrics}))
            if metrics["mean_reciprocal_rank"] > best_mrr:
                best_mrr = metrics["mean_reciprocal_rank"]
                best_state = {key: value.detach().cpu().clone() for key, value in model.state_dict().items()}
    if best_state is None:
        raise RuntimeError("Nenhum checkpoint candidato foi avaliado.")
    model.load_state_dict(best_state)
    after = retrieval_metrics(model, tokenizer, eval_pairs, device)
    accepted = after["mean_reciprocal_rank"] > before["mean_reciprocal_rank"]
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = {
        "model_state": model.state_dict(),
        "model_config": model.config_dict(),
        "tokenizer_version": TOKENIZER_VERSION,
        "training_method": "symmetric_in_batch_info_nce",
        "training_pairs_sha256": train_hash,
        "evaluation_pairs_sha256": eval_hash,
        "training_pairs": len(train_pairs),
        "evaluation_pairs": len(eval_pairs),
        "seed": args.seed,
        "steps": args.steps,
        "baseline_metrics": before,
        "candidate_metrics": after,
        "candidate_accepted": accepted,
        "experimental": True,
    }
    temporary = output.with_suffix(output.suffix + ".tmp")
    torch.save(checkpoint, temporary)
    temporary.replace(output)
    return {
        "checkpoint": str(output),
        "baseline": before,
        "candidate": after,
        "accepted_for_experiment": accepted,
        "promotion": "blocked_pending_human_review_and_larger_benchmark",
        "warning": "Benchmark pequeno; não comprova semântica geral nem autoriza promoção em produção.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train-pairs", default="training/semantic/train.pt-br.jsonl")
    parser.add_argument("--eval-pairs", default="training/semantic/eval.pt-br.jsonl")
    parser.add_argument("--output", default="artifacts/ultron-semantic-encoder.pt")
    parser.add_argument("--steps", type=int, default=300)
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--temperature", type=float, default=0.08)
    parser.add_argument("--learning-rate", type=float, default=2e-4)
    parser.add_argument("--eval-interval", type=int, default=25)
    parser.add_argument("--context-length", type=int, default=128)
    parser.add_argument("--width", type=int, default=64)
    parser.add_argument("--layers", type=int, default=2)
    parser.add_argument("--heads", type=int, default=4)
    parser.add_argument("--seed", type=int, default=31)
    parser.add_argument("--threads", type=int, default=2)
    args = parser.parse_args()
    print(json.dumps(train(args), ensure_ascii=False))


if __name__ == "__main__":
    main()
