"""Validate a freshly trained ULTRON checkpoint on CPU and measure its footprint."""
from __future__ import annotations

import argparse
import json
import math
import resource
import time
from pathlib import Path

import torch

from .model import ModelConfig, UltronTinyGPT
from .tokenizer import BOS_ID, ByteTokenizer, TrainedBPETokenizer


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--tokenizer-json", default=None)
    parser.add_argument("--threads", type=int, default=2)
    parser.add_argument("--tokens", type=int, default=24)
    args = parser.parse_args()
    if not 1 <= args.threads <= 4 or not 1 <= args.tokens <= 128:
        parser.error("threads must be 1..4 and tokens must be 1..128")

    torch.set_num_threads(args.threads)
    checkpoint = torch.load(args.checkpoint, map_location="cpu", weights_only=True)
    config = ModelConfig(**checkpoint["model_config"])
    if args.tokenizer_json:
        import hashlib
        tokenizer = TrainedBPETokenizer(args.tokenizer_json)
        tokenizer_hash = hashlib.sha256(Path(args.tokenizer_json).read_bytes()).hexdigest()
        if checkpoint.get("tokenizer_json_sha256") != tokenizer_hash:
            raise RuntimeError("Tokenizer checksum does not match the checkpoint")
        prompt_ids = [tokenizer.bos_id, *tokenizer.encode(prompt, add_special_tokens=False)]
    else:
        tokenizer = ByteTokenizer()
        if checkpoint.get("tokenizer_version") != tokenizer.version:
            raise RuntimeError("Checkpoint requires its matching tokenizer JSON")
        prompt_ids = tokenizer.encode(prompt)
    if config.vocab_size != tokenizer.vocab_size:
        raise RuntimeError("Checkpoint and tokenizer vocabulary sizes differ")
    model = UltronTinyGPT(config)
    model.load_state_dict(checkpoint["model_state"], strict=True)
    model.eval()

    prompt = "O ULTRON aprende com testes e dados de qualidade."
    input_ids = torch.tensor([prompt_ids], dtype=torch.long)
    started = time.perf_counter()
    with torch.inference_mode():
        generated = model.generate(input_ids, max_new_tokens=args.tokens, temperature=0)
    elapsed = time.perf_counter() - started
    decoded = tokenizer.decode(generated[0].tolist())
    if not decoded.startswith(prompt) or len(decoded) <= len(prompt):
        raise RuntimeError("Checkpoint generation smoke test returned an invalid result")

    # Linux reports ru_maxrss in KiB. This is a runner-side measurement, not iPhone RAM.
    peak_rss_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
    report = {
        "checkpoint": str(args.checkpoint),
        "valid_state_dict": True,
        "generation_smoke_test": "passed",
        "tokenizer": tokenizer.version,
        "parameters": model.parameter_count(),
        "training_steps": checkpoint.get("training_steps"),
        "validation_loss": checkpoint.get("validation_loss"),
        "validation_perplexity": checkpoint.get("validation_perplexity"),
        "generation_tokens": args.tokens,
        "generation_total_ms": round(elapsed * 1000, 3),
        "generation_ms_per_token": round(elapsed * 1000 / args.tokens, 3),
        "runner_peak_rss_mb": round(peak_rss_mb, 2),
        "device_ram_claim": False,
        "sample": decoded,
        "experimental_only": True,
    }
    if not math.isfinite(float(report["validation_loss"])):
        raise RuntimeError("Validation loss is not finite")
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
