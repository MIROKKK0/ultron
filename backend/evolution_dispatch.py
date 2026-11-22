"""Authenticated dispatch of ULTRON's recursive-evolution GitHub Actions worker."""
from __future__ import annotations

import os
import re

import httpx


def dispatch_evolution_workflow(objective: str = "") -> dict:
    token = os.getenv("ULTRON_GITHUB_TOKEN", "")
    repository = os.getenv("ULTRON_GITHUB_REPOSITORY", "MIROKKK0/ultron")
    workflow_ref = os.getenv("ULTRON_EVOLUTION_WORKFLOW_REF", "main")
    if not token:
        raise RuntimeError("ULTRON_GITHUB_TOKEN não está configurado no Render.")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise RuntimeError("Repositório de evolução inválido.")
    if len(objective) > 1000:
        raise ValueError("O objetivo deve ter no máximo 1000 caracteres.")
    url = f"https://api.github.com/repos/{repository}/actions/workflows/recursive-evolution.yml/dispatches"
    try:
        response = httpx.post(
            url,
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
            json={"ref": workflow_ref, "inputs": {"objective": objective.strip()}},
            timeout=httpx.Timeout(20.0, connect=8.0),
        )
    except httpx.HTTPError as exc:
        raise RuntimeError("Não foi possível contactar o GitHub Actions.") from exc
    if response.status_code != 204:
        raise RuntimeError(f"GitHub recusou o disparo do worker (HTTP {response.status_code}).")
    return {
        "dispatched": True,
        "workflow": "recursive-evolution.yml",
        "workflow_ref": workflow_ref,
        "development_target": "feat/ultron-core-assistant",
        "objective": objective.strip() or "O ULTRON escolhe a melhoria mais valiosa após pesquisar e inspecionar o projeto.",
        "promotion": "O agente revisa e incorpora candidatos aprovados no ramo de desenvolvimento; não publica diretamente no main nem implanta o Render.",
    }
