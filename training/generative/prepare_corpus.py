#!/usr/bin/env python3
"""Prepare a bounded, provenance-preserving PT-BR public-domain corpus sample."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from pathlib import Path


DATASET_ID = "dataseek/ptbr-books-publicos"
DATASET_LICENSE = "CC0-1.0"
EMAIL = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
CPF = re.compile(r"\b\d{3}[. ]?\d{3}[. ]?\d{3}[- ]?\d{2}\b")
CNPJ = re.compile(r"\b\d{2}[. ]?\d{3}[. ]?\d{3}/?\d{4}[- ]?\d{2}\b")
PHONE = re.compile(r"(?<!\d)(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?9?\d{4}[- .]?\d{4}(?!\d)")
URL = re.compile(r"(?i)\bhttps?://\S+")


def clean_text(raw: str) -> str:
    text = unicodedata.normalize("NFKC", str(raw))
    text = "".join(char for char in text if char >= " " or char in "\n\t")
    text = EMAIL.sub("[EMAIL]", text)
    text = CPF.sub("[CPF]", text)
    text = CNPJ.sub("[CNPJ]", text)
    text = PHONE.sub("[TELEFONE]", text)
    text = URL.sub("[URL]", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def alpha_ratio(text: str) -> float:
    visible = [char for char in text if not char.isspace()]
    if not visible:
        return 0.0
    return sum(char.isalpha() for char in visible) / len(visible)


def split_for_document(text_hash: str) -> str:
    bucket = int(text_hash[:8], 16) % 100
    return "train" if bucket < 80 else ("validation" if bucket < 90 else "test")


def prepare(args: argparse.Namespace) -> dict:
    # Import lazily so cleaning functions and tests need no Hugging Face dependency.
    from datasets import load_dataset

    output = Path(args.output_dir)
    output.mkdir(parents=True, exist_ok=True)
    handles = {
        name: (output / f"{name}.txt").open("w", encoding="utf-8")
        for name in ("train", "validation", "test")
    }
    seen: set[str] = set()
    counts = {name: 0 for name in handles}
    chars = {name: 0 for name in handles}
    filtered = {"short": 0, "low_alpha": 0, "duplicate": 0, "empty": 0}
    provenance = []
    total_chars = 0
    try:
        dataset = load_dataset(DATASET_ID, split="train", streaming=True)
        for row in dataset:
            text = clean_text(row.get("text", ""))
            if not text:
                filtered["empty"] += 1
                continue
            if len(text) < args.min_chars:
                filtered["short"] += 1
                continue
            if alpha_ratio(text) < args.min_alpha_ratio:
                filtered["low_alpha"] += 1
                continue
            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
            if digest in seen:
                filtered["duplicate"] += 1
                continue
            seen.add(digest)
            split = split_for_document(digest)
            if total_chars + len(text) > args.max_chars:
                break
            handles[split].write(text + "\n")
            counts[split] += 1
            chars[split] += len(text) + 1
            total_chars += len(text) + 1
            provenance.append({
                "sha256": digest,
                "split": split,
                "source_dataset": DATASET_ID,
                "license": DATASET_LICENSE,
                "document_id": str(row.get("id", ""))[:100],
                "filename": str(row.get("filename", ""))[:200],
            })
            if total_chars >= args.max_chars:
                break
    finally:
        for handle in handles.values():
            handle.close()

    for name in handles:
        if chars[name] <= args.context_length + 2:
            raise ValueError(f"Split {name} ficou pequeno demais; aumente --max-chars.")
    manifest = {
        "dataset": DATASET_ID,
        "license": DATASET_LICENSE,
        "attribution": "Dataseek / Magestic.ai; upstream Brazilian public-domain works",
        "max_chars": args.max_chars,
        "documents": counts,
        "characters": chars,
        "filtered": filtered,
        "pii_masks": ["email", "cpf", "cnpj", "phone", "url"],
        "pii_warning": "Regex masking is incomplete; review samples before public release.",
        "files": {
            name: hashlib.sha256((output / f"{name}.txt").read_bytes()).hexdigest()
            for name in handles
        },
    }
    (output / "provenance.jsonl").write_text(
        "".join(json.dumps(item, ensure_ascii=False) + "\n" for item in provenance),
        encoding="utf-8",
    )
    (output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", default="artifacts/ptbr-corpus")
    parser.add_argument("--max-chars", type=int, default=500_000)
    parser.add_argument("--min-chars", type=int, default=500)
    parser.add_argument("--min-alpha-ratio", type=float, default=0.65)
    parser.add_argument("--context-length", type=int, default=128)
    args = parser.parse_args()
    if args.max_chars < 100_000 or args.min_chars < 100 or not 0.0 < args.min_alpha_ratio < 1.0:
        parser.error("Use --max-chars >= 100000, --min-chars >= 100 e alpha ratio entre 0 e 1.")
    print(json.dumps(prepare(args), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
