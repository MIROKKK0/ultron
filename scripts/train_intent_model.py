#!/usr/bin/env python3
"""Train ULTRON's small intent classifier from its own reviewed corpus."""
from __future__ import annotations

import argparse
import collections
import json
import math
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORPUS = ROOT / "training" / "intent_corpus.jsonl"
OUTPUT = ROOT / "backend" / "model" / "intent_model.json"
BUCKETS = 4096
ALPHA = 0.25

def token_id(value: str) -> int:
    result = 2166136261
    for byte in value.encode("utf-8"):
        result ^= byte
        result = (result * 16777619) & 0xFFFFFFFF
    return result % BUCKETS

def tokenize(text: str) -> dict[int, int]:
    normalized = unicodedata.normalize("NFKC", text.casefold())
    result: dict[int, int] = {}
    for word in re.findall(r"[a-zà-ÿ0-9]+", normalized):
        if len(word) > 1:
            idx = token_id("w:" + word)
            result[idx] = result.get(idx, 0) + 2
    padded = [94, *normalized.encode("utf-8"), 36]
    for size in (2, 3):
        for start in range(len(padded) - size + 1):
            gram = bytes(padded[start:start + size]).decode("latin1")
            idx = token_id(gram)
            result[idx] = result.get(idx, 0) + 1
    return result

def load_corpus() -> dict[str, list[str]]:
    data: dict[str, list[str]] = collections.defaultdict(list)
    for line in CORPUS.read_text(encoding="utf-8").splitlines():
        if line.strip():
            item = json.loads(line)
            intent, text = item["intent"], item["text"].strip()
            if not intent or not text:
                raise ValueError("Corpus contém intent/text vazio.")
            data[intent].append(text)
    if len(data) < 3 or sum(map(len, data.values())) < 30:
        raise ValueError("Corpus ULTRON pequeno demais.")
    return dict(data)

def train(data: dict[str, list[str]]) -> dict:
    classes = {}
    for label in sorted(data):
        counts: collections.Counter[int] = collections.Counter()
        total = documents = 0
        for text in data[label]:
            features = tokenize(text)
            counts.update(features)
            total += sum(features.values())
            documents += 1
        classes[label] = {
            "documents": documents,
            "total_features": total,
            "counts": [[idx, count] for idx, count in sorted(counts.items())],
        }
    return {
        "version": "ultron-intent-nb-1",
        "tokenizer": "ultron-hash-word-byte-ngram-v1",
        "buckets": BUCKETS,
        "alpha": ALPHA,
        "classes": classes,
        "training_examples": sum(len(items) for items in data.values()),
    }

def accuracy(data: dict[str, list[str]]) -> float:
    correct = total = 0
    for expected, examples in data.items():
        for text in examples:
            features = tokenize(text)
            scores = {}
            docs = sum(len(items) for items in data.values())
            for label, items in data.items():
                counts = collections.Counter()
                for item in items:
                    counts.update(tokenize(item))
                feature_total = sum(counts.values())
                score = math.log(len(items) / docs)
                denominator = feature_total + ALPHA * BUCKETS
                for idx, count in features.items():
                    score += count * math.log((counts.get(idx, 0) + ALPHA) / denominator)
                scores[label] = score
            predicted = max(scores, key=scores.get)
            correct += predicted == expected
            total += 1
    return correct / max(1, total)

def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    data = load_corpus()
    model = train(data)
    rendered = json.dumps(model, ensure_ascii=False, separators=(",", ":"), sort_keys=True) + "\n"
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != rendered:
            raise SystemExit("Modelo versionado difere do corpus; execute o treino e revise o diff.")
        print(f"Modelo verificado: {model['training_examples']} exemplos, {len(model['classes'])} classes.")
        return 0
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(rendered, encoding="utf-8")
    print(f"Modelo ULTRON treinado: {model['training_examples']} exemplos, {len(model['classes'])} classes, {OUTPUT.stat().st_size} bytes.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
