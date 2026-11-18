"""Relevant public web and video search for ULTRON."""
from __future__ import annotations

import re
import math
import ipaddress
import unicodedata
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode

VIDEO_TERMS = re.compile(
    r"\b(v[ií]deo|v[ií]deos|youtube|clipe|gameplay|trailer|shorts?)\b",
    re.IGNORECASE,
)
STOP_WORDS = {
    "para", "com", "sem", "sobre", "mais", "melhor", "video", "videos",
    "youtube", "vídeo", "vídeos", "quero", "procure", "pesquise", "encontre", "mostre",
    "por", "uma", "uns", "dos", "das", "que", "de", "do", "da", "no", "na", "em", "e", "um", "the", "and", "for",
}


def _terms(value: str) -> set[str]:
    # Normalize accents so "vídeo", "videos" and provider title variants
    # compare consistently without treating generic intent words as topics.
    normalized = unicodedata.normalize("NFKD", value.casefold())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    return {
        token
        for token in re.findall(r"[a-z0-9]{2,}", normalized)
        if token not in STOP_WORDS
    }


def _relevance(query: str, title: str, snippet: str = "") -> float:
    wanted = _terms(query)
    if not wanted:
        return 1.0
    title_terms = _terms(title)
    all_terms = title_terms | _terms(snippet)
    title_score = len(wanted & title_terms) / len(wanted)
    total_score = len(wanted & all_terms) / len(wanted)
    return min(1.0, title_score * 0.7 + total_score * 0.3)


def _canonical_url(url: str) -> str | None:
    try:
        parsed = urlparse(url.strip())
        host = (parsed.hostname or "").lower().rstrip(".")
        if parsed.scheme.lower() != "https" or not host or host in {"localhost", "localhost.localdomain"}:
            return None
        try:
            address = ipaddress.ip_address(host)
            if not address.is_global:
                return None
        except ValueError:
            if "." not in host or any(not part for part in host.split(".")):
                return None
        query = [(key, value) for key, value in parse_qsl(parsed.query, keep_blank_values=True)
                 if not key.lower().startswith("utm_") and key.lower() not in {"fbclid", "gclid", "ref"}]
        return urlunparse(("https", host, parsed.path or "/", "", urlencode(query), ""))
    except (ValueError, TypeError):
        return None


def _bm25_scores(query: str, documents: list[tuple[str, str]]) -> list[float]:
    """Small-corpus BM25 reranker; deterministic and dependency-free."""
    query_terms = _terms(query)
    tokenized = [list(_terms(title) | _terms(snippet)) for title, snippet in documents]
    if not tokenized or not query_terms:
        return [0.0] * len(tokenized)
    avg_len = sum(map(len, tokenized)) / max(1, len(tokenized))
    scores = []
    for tokens in tokenized:
        score = 0.0
        length = len(tokens)
        for term in query_terms:
            frequency = tokens.count(term)
            if not frequency:
                continue
            document_frequency = sum(1 for doc in tokenized if term in doc)
            inverse = math.log(1 + (len(tokenized) - document_frequency + 0.5) / (document_frequency + 0.5))
            denominator = frequency + 1.2 * (1 - 0.75 + 0.75 * length / max(1.0, avg_len))
            score += inverse * frequency * 2.2 / denominator
        scores.append(score)
    maximum = max(scores, default=0.0)
    return [score / maximum if maximum else 0.0 for score in scores]


def _source_prior(url: str) -> float:
    host = (urlparse(url).hostname or "").lower()
    if host.endswith(".gov") or host.endswith(".gov.br"):
        return 1.0
    if host.endswith(".edu") or host.endswith(".edu.br"):
        return 0.95
    if host.endswith(".org"):
        return 0.82
    return 0.65


def _youtube_host(url: str) -> bool:
    try:
        host = (urlparse(url).hostname or "").lower()
    except ValueError:
        return False
    return host == "youtu.be" or host == "youtube.com" or host.endswith(".youtube.com")


def _video_search(query: str, max_results: int, searcher: Any = None) -> list[dict]:
    if searcher is None:
        from ddgs import DDGS
        client = DDGS(timeout=12)
        searcher = client.videos
    raw = searcher(
        query,
        region="br-pt",
        safesearch="moderate",
        max_results=max(1, min(max_results * 3, 20)),
    )
    results = []
    for item in raw or []:
        title = str(item.get("title", "")).strip()[:300]
        original_url = str(item.get("content", item.get("url", ""))).strip()
        url = _canonical_url(original_url)
        snippet = str(item.get("description", item.get("body", ""))).strip()[:1200]
        if not title or not url or not _youtube_host(url):
            continue
        score = _relevance(query, title, snippet)
        if score < 0.12:
            continue
        results.append({
            "title": title,
            "url": url,
            "snippet": snippet,
            "relevance": round(score, 3),
            "type": "video",
            "publisher": str(item.get("publisher", "YouTube"))[:120],
            "duration": str(item.get("duration", ""))[:40],
        })
    results.sort(key=lambda item: item["relevance"], reverse=True)
    return results[:max_results]


def search_web(query: str, max_results: int = 6, searcher: Callable[..., Any] | None = None) -> dict:
    cleaned = " ".join(query.split())
    if not cleaned:
        raise ValueError("Informe o que o ULTRON deve pesquisar.")
    if len(cleaned) > 500:
        raise ValueError("A pesquisa deve ter no máximo 500 caracteres.")
    limit = max(1, min(int(max_results), 8))

    if VIDEO_TERMS.search(cleaned):
        try:
            videos = _video_search(cleaned, limit, searcher)
        except Exception as exc:
            raise RuntimeError("A pesquisa de vídeos falhou temporariamente.") from exc
        if not videos:
            return {
                "query": cleaned,
                "count": 0,
                "results": [],
                "search_type": "video",
                "summary": (
                    "Não encontrei vídeos do YouTube suficientemente relacionados. "
                    "Tente acrescentar o nome do jogo, pessoa ou assunto."
                ),
            }
        summary = "\n".join(
            f"{index}. {item['title']}\n   {item['snippet']}\n   Duração: {item['duration'] or 'não informada'}\n   YouTube: {item['url']}"
            for index, item in enumerate(videos, 1)
        )
        return {
            "query": cleaned,
            "count": len(videos),
            "results": videos,
            "search_type": "video",
            "summary": "Vídeos do YouTube encontrados e ordenados por relevância:\n" + summary,
        }

    if searcher is None:
        from ddgs import DDGS
        searcher = DDGS(timeout=12).text
    raw = []
    last_error: Exception | None = None
    # Keep the fast automatic route first, then widen to every text engine
    # supported by DDGS. A single blocked provider should not disable research.
    for backend in ("auto", "bing,duckduckgo,yahoo,startpage", "all"):
        try:
            raw = searcher(
                cleaned,
                region="br-pt",
                safesearch="moderate",
                max_results=max(1, min(limit * 2, 16)),
                backend=backend,
            )
            if raw:
                break
        except Exception as exc:
            last_error = exc
    if not raw and last_error is not None:
        raise RuntimeError("Todos os mecanismos de pesquisa falharam temporariamente.") from last_error

    candidates = []
    seen = set()
    for item in raw or []:
        title = str(item.get("title", "")).strip()[:300]
        original_url = str(item.get("href", item.get("url", ""))).strip()
        url = _canonical_url(original_url)
        snippet = str(item.get("body", item.get("description", ""))).strip()[:1200]
        if not title or not url or url in seen:
            continue
        seen.add(url)
        candidates.append({
            "title": title, "url": url, "snippet": snippet,
            "type": "web", "published_at": str(item.get("date", item.get("published", "")))[:80],
            "domain": urlparse(url).hostname or "",
            "source_verification": "url_validated_content_not_independently_verified",
        })
    bm25 = _bm25_scores(cleaned, [(item["title"], item["snippet"]) for item in candidates])
    for item, lexical_score in zip(candidates, bm25):
        overlap = _relevance(cleaned, item["title"], item["snippet"])
        item["relevance"] = round(0.65 * lexical_score + 0.25 * overlap + 0.10 * _source_prior(item["url"]), 3)
    results = [item for item in candidates if item["relevance"] >= 0.12]
    results.sort(key=lambda item: item["relevance"], reverse=True)
    results = results[:limit]
    if not results:
        return {
            "query": cleaned,
            "count": 0,
            "results": [],
            "search_type": "web",
            "summary": "A busca não retornou resultados suficientemente relacionados. Tente reformular a consulta.",
        }
    summary = "\n".join(
        f"{index}. {item['title']}\n   {item['snippet']}\n   Relevância: {item['relevance']:.0%}\n   Fonte: {item['url']}"
        for index, item in enumerate(results, 1)
    )
    return {
        "query": cleaned,
        "count": len(results),
        "results": results,
        "search_type": "web",
        "summary": "Resultados encontrados na web, ordenados por relevância:\n" + summary,
    }
