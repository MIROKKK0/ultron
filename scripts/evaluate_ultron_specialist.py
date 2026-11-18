"""Evaluate ULTRON Tiny on held-out, task-specific behavioral cases.

This is a transparent lexical rubric, not a human-quality or factuality judge.
"""
from __future__ import annotations

import argparse
import json
import unicodedata
from pathlib import Path

import torch

from training.generative.model import ModelConfig, UltronTinyGPT
from training.generative.tokenizer import ByteTokenizer


def normalize(text: str) -> str:
    value = unicodedata.normalize("NFKD", text.casefold())
    return " ".join("".join(c for c in value if not unicodedata.combining(c)).split())


def evaluate(checkpoint_path: str, dataset_path: str, max_new_tokens: int = 120, seed: int = 17) -> dict:
    rows = [json.loads(line) for line in Path(dataset_path).read_text(encoding="utf-8").splitlines() if line.strip()]
    cases = [row for row in rows if row.get("split") == "eval"]
    if not cases:
        raise ValueError("Dataset has no held-out eval cases")
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    config = ModelConfig(**checkpoint["model_config"])
    # Recreate the same seeded, untrained initialization used before SFT.
    torch.manual_seed(seed)
    baseline_model = UltronTinyGPT(config)
    baseline_model.eval()
    model = UltronTinyGPT(config)
    model.load_state_dict(checkpoint["model_state"], strict=True)
    model.eval()
    tokenizer = ByteTokenizer()

    def score_model(candidate_model):
        results = []
        for case in cases:
            prompt = tokenizer.encode("Usuário: " + case["prompt"] + "\\nULTRON: ")
            inputs = torch.tensor([prompt[-candidate_model.config.context_length:]], dtype=torch.long)
            with torch.inference_mode():
                output = candidate_model.generate(inputs, max_new_tokens=max_new_tokens, eos_token_id=257)
            generated = tokenizer.decode(output[0, inputs.shape[1]:].tolist()).strip()
            normalized = normalize(generated)
            required = [normalize(term) for term in case.get("required_terms", [])]
            hits = [term for term in required if term and term in normalized]
            score = len(hits) / max(1, len(required))
            results.append({
                "prompt": case["prompt"],
                "score": round(score, 3),
                "passed": bool(required) and score >= 0.66,
                "matched_criteria": hits,
                "required_criteria": required,
                "candidate": generated[:1000],
            })
        return results

    baseline_results = score_model(baseline_model)
    trained_results = score_model(model)
    baseline_pass_rate = sum(1 for item in baseline_results if item["passed"]) / len(baseline_results)
    trained_pass_rate = sum(1 for item in trained_results if item["passed"]) / len(trained_results)
    baseline_coverage = sum(item["score"] for item in baseline_results) / len(baseline_results)
    trained_coverage = sum(item["score"] for item in trained_results) / len(trained_results)
    return {
        "benchmark": "ultron-specialist-v1",
        "checkpoint": str(checkpoint_path),
        "dataset_sha256": checkpoint.get("dataset_sha256"),
        "seed": seed,
        "eval_cases": len(trained_results),
        "baseline_untrained_pass_rate": round(baseline_pass_rate, 3),
        "trained_pass_rate": round(trained_pass_rate, 3),
        "pass_rate_delta": round(trained_pass_rate - baseline_pass_rate, 3),
        "baseline_criterion_coverage": round(baseline_coverage, 3),
        "trained_criterion_coverage": round(trained_coverage, 3),
        "criterion_coverage_delta": round(trained_coverage - baseline_coverage, 3),
        "metric_warning": "Lexical criteria coverage only; not proof of factuality, safety or human-rated answer quality. Promotion requires human A/B review.",
        "baseline_results": baseline_results,
        "results": trained_results,
    }

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--checkpoint", required=True)
    parser.add_argument("--dataset", default="training/generative/ultron_specialist_v1.jsonl")
    parser.add_argument("--output", default="ultron-specialist-eval.json")
    parser.add_argument("--seed", type=int, default=17)
    args = parser.parse_args()
    report = evaluate(args.checkpoint, args.dataset, seed=args.seed)
    Path(args.output).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in report.items() if k != "results"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
