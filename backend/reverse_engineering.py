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
READ_ONLY_PREFIXES = ("analyze_", "inspect_", "list_", "compare_", "read_", "decode_", "disassemble_", "export_", "get_", "find_", "search_")
READ_ONLY_EXACT = {"open_binary", "capture_web_screenshot", "observe_web_session", "export_evidence_bundle"}


class ToolCallRequest(BaseModel):
    arguments: dict[str, Any] = Field(default_factory=dict)

class IPAAnalyzeRequest(BaseModel):
    file_path: str = Field(min_length=1, max_length=1024)


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
    if not (name.startswith(READ_ONLY_PREFIXES) or name in READ_ONLY_EXACT):
        raise HTTPException(status_code=403, detail="Ferramenta bloqueada pela política de análise somente leitura.")
    response = await _request(
        "POST",
        f"/api/tools/{name}/call",
        json={"arguments": payload.arguments},
    )
    return response.json()


@router.post("/ipa/analyze")
async def rea_analyze_ipa(payload: IPAAnalyzeRequest) -> dict[str, Any]:
    # Only paths returned by this bridge's upload endpoint may be opened.
    normalized = payload.file_path.replace("\\", "/")
    if not normalized.startswith("/tmp/rea-uploads/") or ".." in normalized.split("/"):
        raise HTTPException(status_code=400, detail="O caminho não pertence à área temporária de uploads do REA.")
    catalog = (await rea_tools())["tools"]
    if not any(item.get("name") == "open_binary" for item in catalog):
        raise HTTPException(status_code=503, detail="O servidor REA não anunciou open_binary.")
    return await rea_call_tool("open_binary", ToolCallRequest(arguments={"path": normalized}))


@router.post("/ipa/upload")
async def rea_upload_ipa(file: UploadFile = File(...)) -> dict[str, Any]:
    filename = re.sub(r"[^A-Za-z0-9._-]", "_", (file.filename or "upload.ipa").replace("\\", "/").split("/")[-1])[:100]
    if not filename.lower().endswith(".ipa"):
        raise HTTPException(status_code=415, detail="Envie um arquivo .ipa válido.")
    file.file.seek(0, 2)
    size = file.file.tell()
    file.file.seek(0)
    if size <= 0:
        raise HTTPException(status_code=400, detail="O arquivo IPA está vazio.")
    if size > MAX_IPA_BYTES:
        raise HTTPException(status_code=413, detail="O IPA excede o limite de 200 MB.")
    response = await _request(
        "POST",
        "/api/upload",
        files={"file": (filename, file.file, "application/octet-stream")},
    )
    result = response.json()
    if not result.get("filePath"):
        raise HTTPException(status_code=502, detail="O REA não retornou o caminho do arquivo enviado.")
    return {
        "id": result.get("id"),
        "fileName": result.get("fileName", filename),
        "size": result.get("size", size),
        "filePath": result["filePath"],
        "next": "Escolha uma ferramenta REA cujo schema aceite caminho de arquivo e passe filePath nos argumentos.",
    }
