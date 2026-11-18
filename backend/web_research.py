"""Relevant public web and video search for ULTRON."""
from __future__ import annotations

import re
from collections.abc import Callable
from typing import Any
from urllib.parse import urlparse

VIDEO_TERMS = re.compile(
    r"\b(v[ií]deo|v[ií]deos|youtube|clipe|gameplay|trailer|shorts?)\b",
    re.IGNORECASE,
)
STOP_WORDS = {
    "para", "com", "sem", "sobre", "mais", "melhor", "video", "videos",
    "youtube", "quero", "procure", "pesquise", "encontre", "mostre",
    "por", "uma", "uns", "dos", "das", "que", "de", "do", "da", "no", "na", "em", "e", "um", "the", "and", "for",
}


def _terms(value: str) -> set[str]:
    return {
        token.casefold()
        for token in re.findall(r"[a-zà-ÿ0-9]{2,}", value)
        if token.casefold() not in STOP_WORDS
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
        url = str(item.get("content", item.get("url", ""))).strip()
        snippet = str(item.get("description", item.get("body", ""))).strip()[:1200]
        if not title or not _youtube_host(url):
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
    for backend in ("auto", "bing,duckduckgo,yahoo,startpage"):
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

    results = []
    seen = set()
    for item in raw or []:
        title = str(item.get("title", "")).strip()[:300]
        url = str(item.get("href", item.get("url", ""))).strip()
        snippet = str(item.get("body", item.get("description", ""))).strip()[:1200]
        if not title or not url.startswith(("https://", "http://")) or url in seen:
            continue
        score = _relevance(cleaned, title, snippet)
        if score < 0.08:
            continue
        seen.add(url)
        results.append({
            "title": title,
            "url": url,
            "snippet": snippet,
            "relevance": round(score, 3),
            "type": "web",
        })
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
