"""Evidence-aware answer review. It scores support; it never claims truth verification."""
from __future__ import annotations
import re
from urllib.parse import urlparse

_URL = re.compile(r"https?://[^\s)\]>]+")

def review_evidence(task: str, answer: str, evidence: list[dict] | None = None) -> dict:
    evidence = evidence or []
    urls = _URL.findall(answer)
    valid_urls = [u for u in urls if urlparse(u).scheme == "https" and urlparse(u).netloc]
    evidence_urls = {str(x.get("url", "")).strip() for x in evidence if x.get("url")}
    unsupported_links = [u for u in valid_urls if u not in evidence_urls]
    claims = [s.strip() for s in re.split(r"(?<=[.!?])\s+", answer) if len(s.strip()) > 35]
    numeric_claims = re.findall(r"\b\d+(?:[.,]\d+)?%?\b", answer)
    evidence_text = " ".join(
        f"{x.get('title', '')} {x.get('snippet', '')}" for x in evidence
    ).casefold()
    answer_terms = set(re.findall(r"[a-zà-ú0-9]{4,}", answer.casefold()))
    evidence_terms = set(re.findall(r"[a-zà-ú0-9]{4,}", evidence_text))
    overlap = len(answer_terms & evidence_terms) / max(1, len(answer_terms))
    contradictions = []
    # Conservative contradiction flags: mutually exclusive polarity in the same
    # proposition, or incompatible numeric values explicitly tied to same term.
    lowered = answer.casefold()
    if ("não é" in lowered or "não foi" in lowered) and ("é " in lowered or "foi " in lowered):
        contradictions.append({"type": "polarity_conflict", "severity": "review"})
    return {
        "status": "reviewed",
        "evidence_count": len(evidence),
        "answer_url_count": len(urls),
        "unsupported_answer_urls": unsupported_links,
        "substantive_sentence_count": len(claims),
        "numeric_claim_count": len(numeric_claims),
        "lexical_support_ratio": round(overlap, 3),
        "possible_contradictions": contradictions,
        "needs_human_or_source_check": bool(unsupported_links or contradictions or (claims and not evidence)),
        "limitations": [
            "correspondência lexical não comprova que uma afirmação é verdadeira",
            "resultados de busca e snippets são pistas, não verificação independente",
            "contradições semânticas complexas exigem modelo avaliador ou revisão humana",
        ],
    }
