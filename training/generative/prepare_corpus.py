"""Stream a licensed PT-BR corpus into a bounded, auditable training text file.

No model weights are downloaded. This script only prepares text data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path

DATASET_ID = "dataseek/ptbr-wiki"
DATASET_REVISION = "main"
LICENSE = "CC-BY-SA-4.0"
SOURCE_URL = "https://huggingface.co/datasets/dataseek/ptbr-wiki"
ATTRIBUTION = (
    "PT-BR Wikipedia dataset curated by Dataseek Team; source: Wikimedia Foundation "
    "(https://dumps.wikimedia.org/ptwiki/); CC BY-SA 4.0."
)
EMAIL_RE = re.compile(r"(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b")
PHONE_RE = re.compile(r"(?<!\w)(?:\+?55\s*)?(?:\(?\d{2}\)?\s*)?\d{4,5}[-.\s]?\d{4}(?!\w)")
URL_RE = re.compile(r"https?://\S+|www\.\S+", re.I)
REPEAT_RE = re.compile(r"(.)\1{12,}", re.S)


def clean_document(value: str) -> str | None:
    text = unicodedata.normalize("NFKC", str(value)).replace("\x00", " ")
    text = "".join(ch for ch in text if ch in "\n\t" or unicodedata.category(ch)[0] != "C")
    text = URL_RE.sub(" ", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) < 200 or len(text) > 100_000:
        return None
    if EMAIL_RE.search(text) or PHONE_RE.search(text):
        return None
    if REPEAT_RE.search(text):
        return None
    letters = sum(ch.isalpha() for ch in text)
    if letters / max(1, len(text)) < 0.45:
        return None
    return text


def prepare(output: Path, max_bytes: int, max_documents: int) -> dict:
    if not 100_000 <= max_bytes <= 50_000_000 or not 1 <= max_documents <= 100_000:
        raise ValueError("max_bytes must be 100KB..50MB and max_documents must be 1..100000")
    try:
        from datasets import load_dataset
    except ImportError as exc:
        raise RuntimeError("Install training/generative/requirements-data.txt first") from exc

    stream = load_dataset(DATASET_ID, split="train", streaming=True)
    seen: set[str] = set()
    documents: list[str] = []
    total_bytes = 0
    scanned = 0
    rejected = 0
    for row in stream:
        scanned += 1
        text = clean_document(row.get("text", ""))
        if not text:
            rejected += 1
            continue
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
        if digest in seen:
            rejected += 1
            continue
        encoded = text.encode("utf-8")
        separator = 2 if documents else 0
        if total_bytes + separator + len(encoded) > max_bytes:
            break
        seen.add(digest)
        documents.append(text)
        total_bytes += separator + len(encoded)
        if len(documents) >= max_documents:
            break

    if len(documents) < 100 or total_bytes < 100_000:
        raise RuntimeError(f"Not enough clean text: {len(documents)} docs / {total_bytes} bytes")

    output.parent.mkdir(parents=True, exist_ok=True)
    corpus = "\n\n".join(documents) + "\n"
    temp = output.with_name(output.name + ".tmp")
    temp.write_text(corpus, encoding="utf-8")
    temp.replace(output)
    manifest = {
        "dataset": DATASET_ID,
        "revision": DATASET_REVISION,
        "source_url": SOURCE_URL,
        "license": LICENSE,
        "attribution": ATTRIBUTION,
        "prepared_at": datetime.now(timezone.utc).isoformat(),
        "documents_kept": len(documents),
        "documents_scanned": scanned,
        "documents_rejected_or_duplicate": rejected,
        "corpus_bytes": len(corpus.encode("utf-8")),
        "corpus_sha256": hashlib.sha256(corpus.encode("utf-8")).hexdigest(),
        "max_bytes": max_bytes,
        "max_documents": max_documents,
        "filters": [
            "NFKC Unicode normalization",
            "control-character removal",
            "URL removal",
            "minimum 200 and maximum 100000 characters",
            "reject obvious email and phone patterns",
            "reject extreme repeated-character spam",
            "minimum 45 percent alphabetic characters",
            "exact SHA-256 deduplication",
        ],
        "limitations": [
            "Regex filters do not reliably remove names or all personal data.",
            "No comprehensive NER, toxicity, copyright, or factuality audit is performed.",
            "Source dataset states it was not PII-scrubbed and contains residual safety risks.",
            "Downstream corpus/model distribution must remain CC-BY-SA-4.0 compatible and include attribution.",
            "This is an experimental bounded sample, not a general-purpose high-quality corpus.",
        ],
    }
    manifest_path = output.with_suffix(output.suffix + ".manifest.json")
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="artifacts/ptbr-corpus.txt")
    parser.add_argument("--max-bytes", type=int, default=20_000_000)
    parser.add_argument("--max-documents", type=int, default=100_000)
    args = parser.parse_args()
    result = prepare(Path(args.output), args.max_bytes, args.max_documents)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
