"""Generate auditable qualitative samples from a ULTRON checkpoint."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import torch

from .model import ModelConfig, UltronTinyGPT
from .tokenizer import ByteTokenizer, TrainedBPETokenizer


DEFAULT_PROMPTS = [
    "Olá! Quem é você?",
    "Explique por que é importante testar software.",
    "Como posso organizar uma tarefa em etapas?",
    "Qual é a capital do Brasil?",
]


def generate_samples(
    checkpoint_path: str,
    prompts: list[str],
    *,
    tokenizer_json: str | None = None,
    max_new_tokens: int = 80,
    temperature: float = 0.0,
    top_k: int | None = None,
    seed: int = 1234,
) -> dict:
    if not 1 <= max_new_tokens <= 256:
        raise ValueError("max_new_tokens must be 1..256")
    if temperature < 0 or (top_k is not None and top_k < 1):
        raise ValueError("Invalid sampling parameters")
    checkpoint_file = Path(checkpoint_path)
    checkpoint = torch.load(checkpoint_file, map_location="cpu", weights_only=True)
    if tokenizer_json:
        tokenizer = TrainedBPETokenizer(tokenizer_json)
        tokenizer_hash = hashlib.sha256(Path(tokenizer_json).read_bytes()).hexdigest()
        if checkpoint.get("tokenizer_json_sha256") != tokenizer_hash:
            raise ValueError("Tokenizer checksum does not match the checkpoint")
    else:
        tokenizer = ByteTokenizer()
        if checkpoint.get("tokenizer_version") != tokenizer.version:
            raise ValueError("Checkpoint requires its matching tokenizer JSON")
    config = ModelConfig(**checkpoint["model_config"])
    if config.vocab_size != tokenizer.vocab_size:
        raise ValueError("Checkpoint and tokenizer vocabulary sizes differ")
    model = UltronTinyGPT(config)
    model.load_state_dict(checkpoint["model_state"], strict=True)
    model.eval()
    generator = torch.Generator(device="cpu").manual_seed(seed)
    results = []
    for prompt in prompts:
        if not prompt.strip():
            continue
        if isinstance(tokenizer, TrainedBPETokenizer):
            prompt_ids = [tokenizer.bos_id, *tokenizer.encode(prompt, add_special_tokens=False)]
            eos_id = tokenizer.eos_id
        else:
            from .tokenizer import BOS_ID, EOS_ID
            prompt_ids = [BOS_ID, *tokenizer.encode(prompt, add_special_tokens=False)]
            eos_id = EOS_ID
        input_ids = torch.tensor([prompt_ids], dtype=torch.long)
        generated = model.generate(
            input_ids,
            max_new_tokens=max_new_tokens,
            temperature=temperature,
            top_k=top_k,
            generator=generator,
        )[0].tolist()
        new_tokens = generated[len(prompt_ids):]
        if eos_id in new_tokens:
            new_tokens = new_tokens[:new_tokens.index(eos_id)]
        results.append({"prompt": prompt, "completion": tokenizer.decode(new_tokens)})
    return {
        "model": "ULTRON Tiny",
        "experimental": True,
        "parameters": checkpoint.get("parameter_count"),
        "training_steps": checkpoint.get("training_steps"),
        "best_step": checkpoint.get("best_step"),
        "tokenizer": tokenizer.version,
        "checkpoint_sha256": hashlib.sha256(checkpoint_file.read_bytes()).hexdigest(),
        "samples": results,
        "warning": "Qualitative samples are not a capability benchmark or proof of factuality.",
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--tokenizer-json", default=None)
    parser.add_argument("--prompt", action="append", dest="prompts")
    parser.add_argument("--max-new-tokens", type=int, default=80)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--seed", type=int, default=1234)
    parser.add_argument("--output", default=None)
    args = parser.parse_args()
    result = generate_samples(
        args.checkpoint,
        args.prompts or DEFAULT_PROMPTS,
        tokenizer_json=args.tokenizer_json,
        max_new_tokens=args.max_new_tokens,
        temperature=args.temperature,
        top_k=args.top_k,
        seed=args.seed,
    )
    rendered = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered + "\n", encoding="utf-8")
    print(rendered)


if __name__ == "__main__":
    main()
