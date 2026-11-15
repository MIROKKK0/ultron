"""Keyless public web search for ULTRON. Results are source-linked, not LLM-generated."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any


def search_web(query: str, max_results: int = 4, searcher: Callable[..., Any] | None = None) -> dict:
    cleaned = " ".join(query.split())
    if not cleaned:
        raise ValueError("Informe o que o ULTRON deve pesquisar.")
    if len(cleaned) > 500:
        raise ValueError("A pesquisa deve ter no máximo 500 caracteres.")
    if searcher is None:
        from ddgs import DDGS
        searcher = DDGS(timeout=6).text
    raw = []
    last_error: Exception | None = None
    # Try auto-discovery first, then a set of independent supported engines.
    for backend in ("auto", "bing,duckduckgo,yahoo,startpage,wikipedia"):
        try:
            raw = searcher(cleaned, region="br-pt", safesearch="moderate",
                           max_results=max(1, min(max_results, 4)), backend=backend)
            if raw:
                break
        except Exception as exc:
            last_error = exc
    if not raw and last_error is not None:
        raise RuntimeError("Todos os mecanismos de pesquisa falharam temporariamente.") from last_error
    results = []
    for item in raw or []:
        title = str(item.get("title", "")).strip()[:300]
        url = str(item.get("href", "")).strip()
        snippet = str(item.get("body", "")).strip()[:1200]
        if title and url.startswith(("https://", "http://")):
            results.append({"title": title, "url": url, "snippet": snippet})
    if not results:
        return {"query": cleaned, "count": 0, "results": [],
                "summary": "A busca não retornou resultados verificáveis. Tente reformular a consulta."}
    summary = "\n".join(
        f"{i}. {item['title']}\n   {item['snippet']}\n   Fonte: {item['url']}"
        for i, item in enumerate(results, 1)
    )
    return {"query": cleaned, "count": len(results), "results": results,
            "summary": "Resultados encontrados na web (síntese por trechos; não é uma resposta gerada por LLM):\n" + summary}
