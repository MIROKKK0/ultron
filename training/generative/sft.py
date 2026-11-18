"""Supervised instruction fine-tuning for ULTRON Tiny using curated JSONL pairs."""
from __future__ import annotations
import argparse, hashlib, json, math, random
from pathlib import Path
import torch
from .model import ModelConfig, UltronTinyGPT
from .tokenizer import ByteTokenizer

def load_pairs(path: str, split: str, context_length: int):
    tokenizer = ByteTokenizer()
    pairs = []
    for line_no, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("split") != split:
            continue
        prompt, completion = row.get("prompt"), row.get("completion")
        if not isinstance(prompt, str) or not isinstance(completion, str) or not prompt.strip() or not completion.strip():
            raise ValueError(f"Linha {line_no}: prompt/completion inválidos")
        prefix = tokenizer.encode("Usuário: " + prompt.strip() + "\\nULTRON: ", add_special_tokens=False)
        answer = tokenizer.encode(completion.strip(), add_special_tokens=False) + [257]
        # Preserve the complete target and the most recent part of long prompts.
        answer = answer[: max(1, context_length // 2)]
        prefix = prefix[-max(1, context_length - len(answer) - 1):]
        tokens = [256, *prefix, *answer]
        if len(tokens) < 3:
            raise ValueError(f"Linha {line_no}: exemplo muito curto")
        input_ids = torch.tensor(tokens[:-1], dtype=torch.long)
        labels = torch.tensor(tokens[1:], dtype=torch.long)
        prompt_target_count = min(len(prefix), len(labels))
        labels[:prompt_target_count] = -100
        pairs.append((input_ids, labels))
    if not pairs:
        raise ValueError(f"Nenhum exemplo no split {split!r}")
    return pairs

@torch.no_grad()
def evaluate(model, pairs):
    model.eval()
    losses = []
    for inputs, labels in pairs:
        _, loss = model(inputs[None, :], labels[None, :])
        if loss is not None and torch.isfinite(loss):
            losses.append(float(loss.item()))
    model.train()
    if not losses:
        raise RuntimeError("Nenhum token-alvo válido na avaliação")
    return sum(losses) / len(losses)

def train(args):
    if args.epochs < 1 or args.learning_rate <= 0 or args.threads < 1 or args.threads > 4:
        raise ValueError("Hiperparâmetros inválidos")
    torch.manual_seed(args.seed)
    random.seed(args.seed)
    torch.set_num_threads(args.threads)
    train_pairs = load_pairs(args.dataset, "train", args.context_length)
    eval_pairs = load_pairs(args.dataset, "eval", args.context_length)
    config = ModelConfig(context_length=args.context_length, width=args.width, layers=args.layers, heads=args.heads, dropout=0.1)
    model = UltronTinyGPT(config)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.learning_rate, weight_decay=0.1)
    best_loss, best_state, best_epoch, stale = float("inf"), None, 0, 0
    for epoch in range(args.epochs):
        model.train()
        order = list(range(len(train_pairs)))
        random.shuffle(order)
        epoch_losses = []
        for index in order:
            inputs, labels = train_pairs[index]
            _, loss = model(inputs[None, :], labels[None, :])
            if loss is None or not torch.isfinite(loss):
                raise RuntimeError("Loss de treino inválida")
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            epoch_losses.append(float(loss.item()))
        eval_loss = evaluate(model, eval_pairs)
        print(json.dumps({"epoch": epoch + 1, "train_loss": round(sum(epoch_losses)/len(epoch_losses), 5),
                          "eval_completion_loss": round(eval_loss, 5),
                          "eval_perplexity": round(math.exp(min(eval_loss, 80)), 5)}))
        if eval_loss < best_loss - args.min_delta:
            best_loss, best_epoch, stale = eval_loss, epoch + 1, 0
            best_state = {k: v.detach().cpu().clone() for k, v in model.state_dict().items()}
        else:
            stale += 1
            if args.patience and stale >= args.patience:
                break
    if best_state is None:
        raise RuntimeError("Treino não produziu checkpoint válido")
    model.load_state_dict(best_state)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    temp = output.with_name(output.name + ".tmp")
    temp_checkpoint = {"model_state": model.state_dict(), "model_config": model.config_dict(),
        "tokenizer_version": ByteTokenizer.version, "training_mode": "supervised_instruction_finetuning",
        "training_steps": len(train_pairs) * best_epoch, "best_epoch": best_epoch,
        "validation_loss": best_loss, "validation_perplexity": math.exp(min(best_loss, 80)),
        "dataset_sha256": hashlib.sha256(Path(args.dataset).read_bytes()).hexdigest(),
        "train_examples": len(train_pairs), "eval_examples": len(eval_pairs),
        "parameter_count": model.parameter_count(), "experimental": True}
    torch.save(temp_checkpoint, temp)
    temp.replace(output)
    return {"checkpoint": str(output), "best_epoch": best_epoch, "train_examples": len(train_pairs),
            "eval_examples": len(eval_pairs), "completion_loss": round(best_loss, 5),
            "perplexity": round(math.exp(min(best_loss, 80)), 5),
            "parameters": model.parameter_count(),
            "warning": "Seed dataset is small; benchmark and human review required before use."}

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--dataset", default="training/generative/instructions_seed.jsonl")
    p.add_argument("--output", default="artifacts/ultron-tiny-sft.pt")
    p.add_argument("--epochs", type=int, default=20)
    p.add_argument("--patience", type=int, default=4)
    p.add_argument("--min-delta", type=float, default=0.001)
    p.add_argument("--learning-rate", type=float, default=1e-4)
    p.add_argument("--context-length", type=int, default=512)
    p.add_argument("--width", type=int, default=64)
    p.add_argument("--layers", type=int, default=2)
    p.add_argument("--heads", type=int, default=4)
    p.add_argument("--seed", type=int, default=17)
    p.add_argument("--threads", type=int, default=2)
    args = p.parse_args()
    print(json.dumps(train(args), ensure_ascii=False))
if __name__ == "__main__":
    main()
