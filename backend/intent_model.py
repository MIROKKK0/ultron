"""Tiny original ULTRON intent model: hashed UTF-8 n-grams + Multinomial Naive Bayes.

This is a trained intent router, not a general-purpose generative language model.
It uses only the Python standard library and a small checked-in ULTRON corpus.
"""
from __future__ import annotations

import json
import math
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from backend.tutor_mode import is_programming_tutor_request

MODEL_PATH = Path(__file__).with_name("model") / "intent_model.json"
ANCHORS = {
    "greeting": ("oi", "olá", "ola", "bom dia", "boa tarde", "boa noite", "e aí", "eai", "saudações"),
    "help": ("ajuda", "comandos", "capacidades", "recursos", "funções", "funcoes", "usar o ultron", "como usar"),
    "identity": ("quem é você", "quem e voce", "seu nome", "qual seu nome", "identidade", "apresente", "arquitetura"),
    "plan": ("planej", "organize", "organizar", "etapas", "roteiro", "plano de ação", "plano de acao"),
    "remember": ("lembre", "lembra", "guarde", "anote", "memorize", "salve essa", "registre"),
    "improve": ("evolu", "melhor", "autoavalia", "autoaperfei", "bugs", "revise sua", "diagnóstico interno", "diagnostico interno"),
    "thanks": ("obrigad", "valeu", "agrade", "brigad", "thanks"),
    "status": ("status", "online", "funcionando", "estado do sistema", "servidor", "operacional", "pronto"),
    "unknown": (),
}

def _bytes(value: str) -> list[int]:
    return list(value.encode("utf-8"))

def _hash_bytes(raw: bytes, buckets: int) -> int:
    result = 2166136261
    for byte in raw:
        result ^= byte
        result = (result * 16777619) & 0xFFFFFFFF
    return result % buckets

def _hash_token(value: str, buckets: int) -> int:
    return _hash_bytes(value.encode("utf-8"), buckets)

def tokenize(text: str, buckets: int = 4096) -> dict[int, int]:
    normalized = unicodedata.normalize("NFKC", text.casefold())
    features: dict[int, int] = {}
    for word in re.findall(r"[a-zà-ÿ0-9]+", normalized):
        if len(word) > 1:
            token_id = _hash_token("w:" + word, buckets)
            features[token_id] = features.get(token_id, 0) + 2
    raw = _bytes(normalized)
    padded = [94, *raw, 36]
    for size in (2, 3):
        for index in range(len(padded) - size + 1):
            gram = bytes(padded[index:index + size])
            token_id = _hash_bytes(gram, buckets)
            features[token_id] = features.get(token_id, 0) + 1
    return features

@lru_cache(maxsize=1)
def load_model() -> dict:
    with MODEL_PATH.open("r", encoding="utf-8") as handle:
        model = json.load(handle)
    if model.get("version") != "ultron-intent-nb-1":
        raise ValueError("Versão incompatível do modelo ULTRON.")
    return model

@lru_cache(maxsize=1)
def _prepared_classes() -> dict:
    model = load_model()
    return {
        label: {
            "documents": item["documents"],
            "total_features": item["total_features"],
            "counts": dict(item["counts"]),
        }
        for label, item in model["classes"].items()
    }

def predict_intent(text: str) -> dict:
    model = load_model()
    classes = _prepared_classes()
    features = tokenize(text, int(model["buckets"]))
    total_documents = sum(item["documents"] for item in classes.values())
    scores: dict[str, float] = {}
    alpha = float(model["alpha"])
    buckets = int(model["buckets"])
    for label, item in classes.items():
        score = math.log(item["documents"] / total_documents)
        denominator = item["total_features"] + alpha * buckets
        counts = item["counts"]
        for token_id, count in features.items():
            score += count * math.log((counts.get(token_id, 0) + alpha) / denominator)
        scores[label] = score
    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    maximum = ranked[0][1]
    exponentials = {label: math.exp(score - maximum) for label, score in scores.items()}
    normalizer = sum(exponentials.values()) or 1.0
    probabilities = [(label, exponentials[label] / normalizer) for label, _ in ranked]
    top = probabilities[0]
    second = probabilities[1][1] if len(probabilities) > 1 else 0.0
    candidate = top[0]
    lowered = unicodedata.normalize("NFKC", text.casefold())
    anchored = candidate == "unknown" or any(anchor in lowered for anchor in ANCHORS.get(candidate, ()))
    if not anchored or top[1] < 0.55 or top[1] - second < 0.08:
        candidate = "unknown"
    return {
        "intent": candidate,
        "candidate": top[0],
        "confidence": round(top[1], 4),
        "margin": round(top[1] - second, 4),
        "tokenizer": model["tokenizer"],
        "model_version": model["version"],
    }

def resolve_intent(text: str) -> dict:
    lowered = unicodedata.normalize("NFKC", text.casefold()).strip()
    if is_programming_tutor_request(lowered):
        intent = "learn_programming"
    elif re.match(r"^/(?:plan|brain)\b", lowered) or re.search(r"\b(planej|planejar|planeje|planejamento|organize|organizar|etapas|roteiro)\w*", lowered):
        intent = "plan"
    elif re.search(r"\b(evolu|melhor|autoavalia|autoaperfei|bugs?|revise sua|diagnóstico interno|diagnostico interno)\w*", lowered):
        intent = "improve"
    elif re.search(r"\b(obrigad|valeu|agrade|brigad|thanks)\w*", lowered):
        intent = "thanks"
    elif lowered in {"ajuda", "help", "/help", "o que você faz", "o que voce faz", "como funciona o ultron", "como usar o ultron"} or re.search(r"\b(ajuda|comandos|capacidades|recursos|funções|funcoes|como usar)\b", lowered):
        intent = "help"
    elif re.match(r"^(oi|olá|ola|bom dia|boa tarde|boa noite|e aí|eai|saudações)\b", lowered):
        intent = "greeting"
    elif re.search(r"\b(quem é você|quem e voce|seu nome|qual seu nome|identidade|apresente-se|arquitetura)\b", lowered):
        intent = "identity"
    elif re.search(r"\b(status|online|funcionando|estado do sistema|servidor|operacional)\b", lowered):
        intent = "status"
    else:
        return predict_intent(text)
    prediction = predict_intent(text)
    return {**prediction, "intent": intent, "routed_by": "verified_skill_guard"}

def model_status() -> dict:
    model = load_model()
    return {
        "configured": True,
        "kind": "intent_classifier",
        "version": model["version"],
        "tokenizer": model["tokenizer"],
        "training_examples": model["training_examples"],
        "classes": len(model["classes"]),
        "artifact_bytes": MODEL_PATH.stat().st_size,
        "generative_language_model": False,
    }
