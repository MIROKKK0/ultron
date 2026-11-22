"""Authenticated ULTRON-to-REA bridge client.

The REA process stays behind its own HTTPS bridge. ULTRON owns the user-facing
identity and installation authentication; REA remains a replaceable specialist.
"""
from __future__ import annotations

import os
import re
import ipaddress
import socket
import uuid
from urllib.parse import urlsplit
import hmac
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from typing import Any

import httpx
from fastapi import APIRouter, File, Header, HTTPException, UploadFile
from pydantic import BaseModel, Field

router = APIRouter()
worker_router = APIRouter()
MAX_IPA_BYTES = 200 * 1024 * 1024
TOOL_NAME = re.compile(r"^[A-Za-z0-9_.-]{1,128}$")
READ_ONLY_PREFIXES = ("analyze_", "inspect_", "list_", "compare_", "read_", "decode_", "disassemble_", "export_", "get_", "find_", "search_")
READ_ONLY_EXACT = {"open_binary", "capture_web_screenshot", "observe_web_session", "export_evidence_bundle"}


class ToolCallRequest(BaseModel):
    arguments: dict[str, Any] = Field(default_factory=dict)

class IPAAnalyzeRequest(BaseModel):
    file_path: str = Field(min_length=1, max_length=1024)

class SiteAnalysisRequest(BaseModel):
    url: str = Field(min_length=8, max_length=2048)
    authorized: bool = False


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



def _validate_public_site_url(value: str) -> str:
    parsed = urlsplit(value.strip())
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise HTTPException(status_code=422, detail="Informe uma URL HTTPS pública sem usuário ou senha.")
    host = parsed.hostname.rstrip(".").lower()
    if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
        raise HTTPException(status_code=422, detail="Endereços locais ou internos não são aceitos.")
    try:
        literal = ipaddress.ip_address(host)
        addresses = [literal]
    except ValueError:
        try:
            records = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
            addresses = [ipaddress.ip_address(record[4][0]) for record in records]
        except OSError as exc:
            raise HTTPException(status_code=422, detail="Não foi possível resolver o domínio informado.") from exc
    if not addresses or any(not address.is_global for address in addresses):
        raise HTTPException(status_code=422, detail="O domínio resolve para uma rede não pública.")
    return value.strip()


def _github_config() -> tuple[str, str, str]:
    token = os.getenv("ULTRON_GITHUB_TOKEN", "").strip()
    repo = os.getenv("ULTRON_GITHUB_REPO", "MIROKKK0/ultron").strip()
    ref = os.getenv("ULTRON_GITHUB_REF", "feat/rea-reverse-engineering-integration").strip()
    if not token:
        raise HTTPException(status_code=503, detail="O worker temporário de sites ainda não foi configurado no servidor.")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo) or not ref:
        raise HTTPException(status_code=503, detail="Configuração do repositório GitHub inválida.")
    return token, repo, ref


async def _github_json(method: str, path: str, *, params: dict[str, Any] | None = None,
                       payload: dict[str, Any] | None = None) -> tuple[int, Any]:
    token, repo, _ = _github_config()
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=10.0)) as client:
            response = await client.request(
                method,
                f"https://api.github.com/repos/{repo}{path}",
                headers=headers,
                params=params,
                json=payload,
            )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Worker GitHub indisponível: {type(exc).__name__}") from exc
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"GitHub Actions respondeu HTTP {response.status_code}: {response.text[:1000]}")
    return response.status_code, (response.json() if response.content else None)


async def _find_site_run(analysis_id: str) -> dict[str, Any] | None:
    _, _, ref = _github_config()
    _, payload = await _github_json(
        "GET",
        "/actions/workflows/rea-site-analysis.yml/runs",
        params={"branch": ref, "event": "workflow_dispatch", "per_page": 20},
    )
    for run in payload.get("workflow_runs", []):
        title = str(run.get("display_title") or run.get("name") or "")
        if analysis_id in title:
            return run
    return None


@router.post("/site/start")
async def rea_start_site_analysis(payload: SiteAnalysisRequest) -> dict[str, Any]:
    if not payload.authorized:
        raise HTTPException(status_code=403, detail="Confirme que você tem autorização para analisar este site.")
    target = _validate_public_site_url(payload.url)
    _, repo, ref = _github_config()
    analysis_id = uuid.uuid4().hex
    await _github_json(
        "POST",
        "/actions/workflows/rea-site-analysis.yml/dispatches",
        payload={
            "ref": ref,
            "inputs": {"analysis_id": analysis_id, "target_url": target},
        },
    )
    run = await _find_site_run(analysis_id)
    return {
        "analysis_id": analysis_id,
        "status": run.get("status", "queued") if run else "dispatched",
        "run_id": run.get("id") if run else None,
        "run_url": run.get("html_url") if run else f"https://github.com/{repo}/actions/workflows/rea-site-analysis.yml",
        "worker": "GitHub-hosted ephemeral runner",
    }


@router.get("/site/status/{analysis_id}")
async def rea_site_analysis_status(analysis_id: str) -> dict[str, Any]:
    if not re.fullmatch(r"[a-f0-9]{32}", analysis_id):
        raise HTTPException(status_code=400, detail="ID de análise inválido.")
    _, repo, _ = _github_config()
    run = await _find_site_run(analysis_id)
    if not run:
        return {
            "analysis_id": analysis_id,
            "status": "queued",
            "run_url": f"https://github.com/{repo}/actions/workflows/rea-site-analysis.yml",
        }
    return {
        "analysis_id": analysis_id,
        "status": run.get("status"),
        "conclusion": run.get("conclusion"),
        "run_id": run.get("id"),
        "run_url": run.get("html_url"),
        "artifacts_url": run.get("artifacts_url"),
    }

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


class AnalysisJobRequest(BaseModel):
    target_type: str
    target_url: str | None = None
    file_id: str | None = None


class WorkerCompletion(BaseModel):
    status: str
    result_summary: str = Field(default="", max_length=60000)
    artifact_name: str = Field(default="ultron-analysis-evidence", max_length=100)
    run_url: str = Field(default="", max_length=1000)
    error: str = Field(default="", max_length=4000)


def _job_db():
    database_url = os.getenv("DATABASE_URL", "")
    if database_url.startswith(("postgres://", "postgresql://")):
        import psycopg
        from psycopg.rows import dict_row
        return psycopg.connect(database_url, row_factory=dict_row)
    connection = sqlite3.connect(os.getenv("ULTRON_DB_PATH", "ultron.db"))
    connection.row_factory = sqlite3.Row
    return connection


def _job_query(db: Any, query: str, params: tuple = ()):
    if db.__class__.__module__.startswith("psycopg"):
        query = query.replace("?", "%s")
    return db.execute(query, params)


def _ensure_jobs_table() -> None:
    with _job_db() as db:
        _job_query(db, """
            CREATE TABLE IF NOT EXISTS reverse_engineering_jobs (
                job_id TEXT PRIMARY KEY,
                owner_id TEXT NOT NULL,
                target_type TEXT NOT NULL,
                target_url TEXT,
                file_id TEXT,
                status TEXT NOT NULL,
                result_json TEXT,
                run_url TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)


def _worker_token_ok(value: str | None) -> bool:
    expected = os.getenv("ULTRON_WORKER_CALLBACK_TOKEN", "")
    supplied = value or ""
    return bool(expected) and hmac.compare_digest(expected, supplied)


def _job_record(job_id: str) -> dict[str, Any] | None:
    _ensure_jobs_table()
    with _job_db() as db:
        row = _job_query(db, "SELECT * FROM reverse_engineering_jobs WHERE job_id=?", (job_id,)).fetchone()
    return dict(row) if row else None


@router.post("/jobs")
async def create_analysis_job(
    payload: AnalysisJobRequest,
    x_installation_id: str | None = Header(default=None),
) -> dict[str, Any]:
    target_type = payload.target_type.lower().strip()
    if target_type not in {"site", "ipa"}:
        raise HTTPException(status_code=400, detail="target_type deve ser site ou ipa.")
    target_url = None
    file_id = None
    if target_type == "site":
        from urllib.parse import urlparse
        parsed = urlparse((payload.target_url or "").strip())
        if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
            raise HTTPException(status_code=400, detail="Informe uma URL HTTPS pública.")
        if parsed.port not in (None, 443):
            raise HTTPException(status_code=400, detail="A análise de sites aceita somente HTTPS na porta padrão.")
        target_url = parsed.geturl()
    else:
        file_id = (payload.file_id or "").strip()
        if not re.fullmatch(r"[0-9a-fA-F-]{36}-[A-Za-z0-9._-]{1,100}", file_id):
            raise HTTPException(status_code=400, detail="Identificador de IPA inválido; envie o arquivo primeiro.")

    token = os.getenv("ULTRON_GITHUB_TOKEN", "")
    repository = os.getenv("ULTRON_GITHUB_REPOSITORY", "MIROKKK0/ultron")
    ref = os.getenv("ULTRON_ANALYSIS_REF", "main")
    if not token:
        raise HTTPException(status_code=503, detail="Configure ULTRON_GITHUB_TOKEN no Render para habilitar os workers.")
    if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repository):
        raise HTTPException(status_code=503, detail="ULTRON_GITHUB_REPOSITORY inválido.")

    _ensure_jobs_table()
    job_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc).isoformat()
    with _job_db() as db:
        _job_query(db, """
            INSERT INTO reverse_engineering_jobs
            (job_id, owner_id, target_type, target_url, file_id, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, 'queued', ?, ?)
        """, (job_id, x_installation_id or "unknown", target_type, target_url, file_id, now, now))

    workflow_url = f"https://api.github.com/repos/{repository}/actions/workflows/reverse-engineering-worker.yml/dispatches"
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            response = await client.post(
                workflow_url,
                headers={
                    "Authorization": f"Bearer {token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                json={"ref": ref, "inputs": {"job_id": job_id}},
            )
        if response.status_code != 204:
            raise RuntimeError(f"GitHub workflow dispatch respondeu HTTP {response.status_code}: {response.text[:1000]}")
    except Exception as exc:
        with _job_db() as db:
            _job_query(db, "UPDATE reverse_engineering_jobs SET status='dispatch_failed', error=?, updated_at=? WHERE job_id=?",
                       (str(exc)[:4000], datetime.now(timezone.utc).isoformat(), job_id))
        raise HTTPException(status_code=502, detail="Não foi possível iniciar o worker isolado do GitHub Actions.") from exc

    return {"job_id": job_id, "status": "queued", "target_type": target_type}


@router.get("/jobs/{job_id}")
async def get_analysis_job(job_id: str, x_installation_id: str | None = Header(default=None)) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9a-fA-F-]{36}", job_id):
        raise HTTPException(status_code=400, detail="Identificador de análise inválido.")
    record = _job_record(job_id)
    if not record or record["owner_id"] != (x_installation_id or "unknown"):
        raise HTTPException(status_code=404, detail="Análise não encontrada.")
    result = json.loads(record["result_json"]) if record.get("result_json") else None
    return {
        "job_id": record["job_id"],
        "status": record["status"],
        "result": result,
        "run_url": record.get("run_url"),
        "error": record.get("error"),
        "updated_at": record["updated_at"],
    }


@worker_router.get("/jobs/{job_id}/payload")
async def worker_job_payload(job_id: str, x_ultron_worker_token: str | None = Header(default=None)) -> dict[str, Any]:
    if not _worker_token_ok(x_ultron_worker_token):
        raise HTTPException(status_code=401, detail="Worker não autorizado.")
    record = _job_record(job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Job não encontrado.")
    with _job_db() as db:
        _job_query(db, "UPDATE reverse_engineering_jobs SET status='running', updated_at=? WHERE job_id=?",
                   (datetime.now(timezone.utc).isoformat(), job_id))
    return {
        "job_id": record["job_id"],
        "target_type": record["target_type"],
        "target_url": record.get("target_url"),
        "file_id": record.get("file_id"),
        "rea_bridge_url": os.getenv("REA_BRIDGE_URL", "").rstrip("/"),
    }


@worker_router.post("/jobs/{job_id}/complete")
async def complete_worker_job(
    job_id: str,
    payload: WorkerCompletion,
    x_ultron_worker_token: str | None = Header(default=None),
) -> dict[str, Any]:
    if not _worker_token_ok(x_ultron_worker_token):
        raise HTTPException(status_code=401, detail="Worker não autorizado.")
    if payload.status not in {"succeeded", "failed"}:
        raise HTTPException(status_code=400, detail="Status final inválido.")
    record = _job_record(job_id)
    if not record:
        raise HTTPException(status_code=404, detail="Job não encontrado.")
    result = {
        "summary": payload.result_summary,
        "artifact_name": payload.artifact_name,
        "run_url": payload.run_url,
    }
    now = datetime.now(timezone.utc).isoformat()
    with _job_db() as db:
        _job_query(db, """
            UPDATE reverse_engineering_jobs
            SET status=?, result_json=?, run_url=?, error=?, updated_at=?
            WHERE job_id=?
        """, (
            payload.status,
            json.dumps(result, ensure_ascii=False),
            payload.run_url,
            payload.error,
            now,
            job_id,
        ))
    return {"ok": True, "job_id": job_id, "status": payload.status}
