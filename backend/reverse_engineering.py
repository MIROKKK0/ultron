"""Authenticated ULTRON-to-REA bridge client.

The REA process stays behind its own HTTPS bridge. ULTRON owns the user-facing
identity and installation authentication; REA remains a replaceable specialist.
"""
from __future__ import annotations

import os
import re
from typing import Any

import httpx
from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel, Field

router = APIRouter()
MAX_IPA_BYTES = 200 * 1024 * 1024
TOOL_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")


class ToolCallRequest(BaseModel):
    arguments: dict[str, Any] = Field(default_factory=dict)


def _bridge_config() -> tuple[str, str]:
    base = os.getenv("REA_BRIDGE_URL", "").strip().rstrip("/")
    token = os.getenv("REA_BRIDGE_TOKEN", "")
    if not base or not token:
        raise HTTPException(
            status_code=503,
            detail="Integração REA não configurada no servidor ULTRON.",
        )
    if not base.startswith("https://"):
        raise HTTPException(status_code=503, detail="O bridge REA precisa usar HTTPS.")
    return base, token


async def _request(method: str, path: str, **kwargs: Any) -> httpx.Response:
    base, token = _bridge_config()
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    headers.update(kwargs.pop("headers", {}))
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(300.0, connect=15.0)) as client:
            response = await client.request(method, f"{base}{path}", headers=headers, **kwargs)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Bridge REA indisponível: {type(exc).__name__}") from exc
    if response.status_code >= 400:
        detail = response.text[:2000]
        raise HTTPException(status_code=502, detail=f"REA respondeu HTTP {response.status_code}: {detail}")
    return response


@router.get("/status")
async def rea_status() -> dict[str, Any]:
    response = await _request("GET", "/api/ready")
    return response.json()


@router.get("/tools")
async def rea_tools() -> dict[str, Any]:
    response = await _request("GET", "/api/tools")
    payload = response.json()
    tools = payload.get("tools", [])
    if not isinstance(tools, list):
        raise HTTPException(status_code=502, detail="Catálogo MCP do REA inválido.")
    return {"tools": tools, "count": len(tools), "provider": "REA MCP"}


@router.post("/tools/{name}/call")
async def rea_call_tool(name: str, payload: ToolCallRequest) -> dict[str, Any]:
    if not TOOL_NAME.fullmatch(name):
        raise HTTPException(status_code=400, detail="Nome de ferramenta inválido.")
    catalog = (await rea_tools())["tools"]
    if not any(item.get("name") == name for item in catalog):
        raise HTTPException(status_code=404, detail="Ferramenta não encontrada no catálogo REA.")
    response = await _request(
        "POST",
        f"/api/tools/{name}/call",
        json={"arguments": payload.arguments},
    )
    return response.json()


@router.post("/ipa/upload")
async def rea_upload_ipa(file: UploadFile = File(...)) -> dict[str, Any]:
    filename = (file.filename or "").replace("\\", "/").split("/")[-1]
    if not filename.lower().endswith(".ipa"):
        raise HTTPException(status_code=415, detail="Envie um arquivo .ipa válido.")
    data = await file.read(MAX_IPA_BYTES + 1)
    if not data:
        raise HTTPException(status_code=400, detail="O arquivo IPA está vazio.")
    if len(data) > MAX_IPA_BYTES:
        raise HTTPException(status_code=413, detail="O IPA excede o limite de 200 MB.")
    response = await _request(
        "POST",
        "/api/upload",
        files={"file": (filename, data, "application/octet-stream")},
    )
    result = response.json()
    if not result.get("filePath"):
        raise HTTPException(status_code=502, detail="O REA não retornou o caminho do arquivo enviado.")
    return {
        "id": result.get("id"),
        "fileName": result.get("fileName", filename),
        "size": result.get("size", len(data)),
        "filePath": result["filePath"],
        "next": "Escolha uma ferramenta REA cujo schema aceite caminho de arquivo e passe filePath nos argumentos.",
    }
