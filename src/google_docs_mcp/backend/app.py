"""Starlette webapp backend — REST glue for the React dashboard + `/mcp` mount.

Per STARLETTE_NO_PYDANTIC_STANDARD.md: plain Starlette, no Pydantic in this layer
(the REST surface here is small and internal — dashboard + tools + skills + a
light local-LLM chat proxy, all consumed by our own Vite SPA).

Known scope reduction vs WEBAPP_SOTA_STANDARDS.md §VI.10 (Cloud Providers): this
backend probes local engines (Ollama/LM Studio/vLLM) for the Chat page but does
NOT implement the full cloud-provider key-vault system (POST /api/settings/llm,
encrypted key storage, per-provider onboarding cards). Declared here and in
docs/DEVELOPMENT.md rather than silently omitted — Chat works with a local
engine only; add cloud providers as a follow-up if the webapp gets real usage.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import re
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

import httpx
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.datastructures import UploadFile
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, Response
from starlette.routing import Mount, Route

from google_docs_mcp import __version__, oauth
from google_docs_mcp.config import settings
from google_docs_mcp.google_client import get_drive_service
from google_docs_mcp.oauth import NotAuthenticatedError, NotConfiguredError
from google_docs_mcp.server import mcp, mcp_http_app
from google_docs_mcp.sync_engine import load_config as load_sync_config
from google_docs_mcp.sync_engine import run_sync_pass
from google_docs_mcp.tools.drive_tool import _EXPORT_MIME_MAP, ExportFormat, google_drive
from google_docs_mcp.tools.libreoffice_tool import google_docs_convert_advanced
from google_docs_mcp.tools.sync_tool import google_docs_sync, sync_config_path, sync_manifest_path

logger = logging.getLogger("google_docs_mcp.backend")

_SKILLS_DIR = Path(__file__).resolve().parents[1] / "skills"

_LOCAL_PROVIDERS = [
    {"name": "Ollama", "port": 11434, "probe": "/api/tags", "kind": "ollama"},
    {"name": "LM Studio", "port": 1234, "probe": "/v1/models", "kind": "openai-compat"},
    {"name": "vLLM", "port": 8000, "probe": "/v1/models", "kind": "openai-compat"},
]

_LOG_BUFFER: list[str] = []

# Sibling fleet repo root — this feature is specific to Sandra's D:\Dev\repos
# fleet layout (many MCP servers, one shared port registry). On any other
# machine this path simply won't exist and Apps Hub degrades to an empty,
# explicitly-labeled list rather than erroring — see api_apps().
_WEBAPP_PORTS_MD = Path(__file__).resolve().parents[4] / "mcp-central-docs" / "operations" / "WEBAPP_PORTS.md"
_PORT_ROW_RE = re.compile(r"^\|\s*(\d{4,5})\s*\|\s*([\w.-]+)\s*\|\s*(.*?)\s*\|\s*$")

# Last background/manual sync pass result, kept in memory for the Sync page's
# status display — not persisted (the manifest itself is the durable state;
# this is just "what happened most recently" for the UI).
_last_sync_result: dict[str, Any] | None = None
_last_sync_error: str | None = None


class BufferLogHandler(logging.Handler):
    """Keeps the last N log lines in memory for GET /api/logs — no file tailing needed."""

    def emit(self, record: logging.LogRecord) -> None:
        _LOG_BUFFER.append(self.format(record))
        del _LOG_BUFFER[:-500]


logging.getLogger("google_docs_mcp").addHandler(BufferLogHandler())


async def api_health(_request: Request) -> JSONResponse:
    status = oauth.get_status()
    return JSONResponse(
        {"status": "ok", "configured": status.configured, "authenticated": status.authenticated}
    )


async def api_dashboard(_request: Request) -> JSONResponse:
    status = oauth.get_status()
    tools = await mcp.list_tools()
    return JSONResponse(
        {
            "version": __version__,
            "configured": status.configured,
            "authenticated": status.authenticated,
            "tool_count": len(tools),
            "scopes": status.scopes,
        }
    )


async def api_tools(_request: Request) -> JSONResponse:
    tools = await mcp.list_tools()
    return JSONResponse(
        {
            "items": [
                {
                    "name": t.name,
                    "description": (t.description or "").split("\n\n")[0],
                    "input_schema": t.parameters,
                }
                for t in tools
            ]
        }
    )


async def api_capabilities(_request: Request) -> JSONResponse:
    """Standard fleet shape for webapp discovery (thin wrapper over /api/tools)."""
    tools = await mcp.list_tools()
    names = sorted(t.name for t in tools)
    return JSONResponse(
        {
            "service": "google-docs-mcp",
            "version": __version__,
            "status": "ok",
            "tool_count": len(names),
            "tools": names,
            "endpoints": ["/api/health", "/api/capabilities", "/api/tools", "/api/dashboard", "/mcp"],
            "transports": ["http", "stdio"],
        }
    )


def _list_skills() -> list[dict[str, str]]:
    if not _SKILLS_DIR.is_dir():
        return []
    return [
        {"name": d.name, "uri": f"skill://{d.name}/SKILL.md"}
        for d in sorted(_SKILLS_DIR.iterdir())
        if d.is_dir() and (d / "SKILL.md").exists()
    ]


async def api_skills(_request: Request) -> JSONResponse:
    return JSONResponse({"items": _list_skills()})


async def api_skill_content(request: Request) -> PlainTextResponse:
    name = request.path_params["name"]
    skill_path = _SKILLS_DIR / name / "SKILL.md"
    if not skill_path.is_file():
        return PlainTextResponse("not found", status_code=404)
    return PlainTextResponse(skill_path.read_text(encoding="utf-8"))


async def get_skill(request: Request) -> PlainTextResponse:
    """Fleet-standard `GET /skill/{name}` alias — see chat_skills_prefab_standard.md §5."""
    return await api_skill_content(request)


async def _probe_provider(client: httpx.AsyncClient, provider: dict[str, Any]) -> dict[str, Any]:
    base = f"http://127.0.0.1:{provider['port']}"
    try:
        resp = await client.get(f"{base}{provider['probe']}", timeout=3.0)
        detected = resp.status_code == 200
    except httpx.HTTPError:
        detected = False
    return {"name": provider["name"], "port": provider["port"], "base": base, "detected": detected}


async def api_llm_providers(_request: Request) -> JSONResponse:
    async with httpx.AsyncClient() as client:
        locals_ = [await _probe_provider(client, p) for p in _LOCAL_PROVIDERS]
    return JSONResponse({"local": locals_})


async def api_llm_models(request: Request) -> JSONResponse:
    """List installed models, and — for Ollama — which are currently loaded.

    `loaded` lets the frontend pick resident-first (never evict a model that's
    already warm in VRAM) instead of blindly defaulting to models[0]. See
    templates/llm-detect/model-preference.ts and BUGS_DEPOT.md BUG-030.
    """
    provider = request.query_params.get("provider", "").lower()
    match = next((p for p in _LOCAL_PROVIDERS if p["name"].lower() == provider), None)
    if not match:
        return JSONResponse(
            {"models": [], "loaded": [], "error": f"unknown provider '{provider}'"}, status_code=400
        )
    base = f"http://127.0.0.1:{match['port']}"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{base}{match['probe']}", timeout=3.0)
            data = resp.json()
            loaded: list[str] = []
            if match["kind"] == "ollama":
                models = [m["name"] for m in data.get("models", [])]
                ps_resp = await client.get(f"{base}/api/ps", timeout=3.0)
                loaded = [m["name"] for m in ps_resp.json().get("models", [])]
            else:
                models = [m["id"] for m in data.get("data", [])]
    except httpx.HTTPError:
        return JSONResponse({"models": [], "loaded": []})
    return JSONResponse({"models": models, "loaded": loaded})


async def api_llm_chat(request: Request) -> JSONResponse:
    """Proxy a chat completion to a detected local engine.

    Never fetched directly from the browser (would break under Tauri and bypass
    CORS handling — see WEBAPP_SOTA_STANDARDS.md §VI.10) — always routed through
    this backend, matching the fleet rule even in this local-engine-only, reduced
    scope (see module docstring).
    """
    body = await request.json()
    provider = str(body.get("provider", ""))
    model = str(body.get("model", ""))
    messages = body.get("messages", [])
    match = next((p for p in _LOCAL_PROVIDERS if p["name"].lower() == provider.lower()), None)
    if not match:
        return JSONResponse({"error": f"unknown or undetected provider '{provider}'"}, status_code=400)

    base = f"http://127.0.0.1:{match['port']}"
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            if match["kind"] == "ollama":
                resp = await client.post(
                    f"{base}/api/chat", json={"model": model, "messages": messages, "stream": False}
                )
                data = resp.json()
                content = data.get("message", {}).get("content", "")
            else:
                resp = await client.post(
                    f"{base}/v1/chat/completions", json={"model": model, "messages": messages}
                )
                data = resp.json()
                content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except httpx.HTTPError as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)
    return JSONResponse({"content": content})


async def api_auth_status(_request: Request) -> JSONResponse:
    return JSONResponse(asdict(oauth.get_status()))


async def api_auth_start(_request: Request) -> JSONResponse:
    """POST — runs the real installed-app OAuth flow (opens the user's browser).

    Blocking (`run_local_server`) is dispatched to a thread pool so it doesn't
    stall the event loop while the user completes browser consent.
    """
    try:
        status = await run_in_threadpool(oauth.run_installed_app_flow)
    except oauth.NotConfiguredError as exc:
        return JSONResponse(
            {"success": False, "error": str(exc), "error_type": "not_configured"}, status_code=400
        )
    return JSONResponse({"success": True, "data": asdict(status)})


async def api_auth_revoke(_request: Request) -> JSONResponse:
    revoked = oauth.revoke()
    return JSONResponse({"success": True, "revoked": revoked})


async def api_onboarding_client(request: Request) -> JSONResponse:
    """POST — persist an OAuth client id/secret pasted into the onboarding wizard.

    A running process can't set its own future environment variables, so this
    writes to `data/oauth_client.json` (0600, gitignored) instead — read as a
    fallback by config.py whenever the env vars aren't set. Env vars always
    win if both are present, so a Claude Desktop config.json setup is never
    silently overridden by a stale wizard entry.
    """
    body = await request.json()
    client_id = str(body.get("client_id", "")).strip()
    client_secret = str(body.get("client_secret", "")).strip()
    if not client_id or not client_secret:
        return JSONResponse(
            {
                "success": False,
                "error": "client_id and client_secret are both required",
                "error_type": "validation",
            },
            status_code=400,
        )
    settings.write_local_client(client_id, client_secret)
    return JSONResponse({"success": True, "data": asdict(oauth.get_status())})


async def api_onboarding_client_clear(_request: Request) -> JSONResponse:
    cleared = settings.clear_local_client()
    return JSONResponse({"success": True, "cleared": cleared, "data": asdict(oauth.get_status())})


async def api_documents(request: Request) -> JSONResponse:
    """Domain page backing endpoint — reuses the real `google_drive` tool function
    directly (not a duplicate REST reimplementation) so the webapp and the MCP
    tool surface can never drift apart."""
    query = request.query_params.get("query")
    cursor = request.query_params.get("cursor")
    result = await google_drive(
        operation="search" if query else "list_files", query=query, cursor=cursor, limit=25
    )
    return JSONResponse(result)


async def api_documents_browse(request: Request) -> JSONResponse:
    """Folder-aware listing for the Documents page's folder navigator."""
    folder_id = request.query_params.get("folder_id") or None
    result = await google_drive(operation="browse", folder_id=folder_id)
    return JSONResponse(result)


async def api_documents_backup(request: Request) -> JSONResponse:
    body = await request.json()
    result = await google_drive(
        operation="backup_folder",
        folder_id=body.get("folder_id"),
        output_dir=body.get("output_dir"),
        export_format=body.get("export_format", "pdf"),
        recursive=bool(body.get("recursive", False)),
    )
    status = 200 if result.get("success") else 400
    return JSONResponse(result, status_code=status)


async def api_document_restore(request: Request) -> JSONResponse:
    file_id = request.path_params["file_id"]
    body = await request.json()
    result = await google_drive(operation="restore_file", file_id=file_id, file_path=body.get("file_path"))
    status = 200 if result.get("success") else 400
    return JSONResponse(result, status_code=status)


async def api_document_convert_advanced(request: Request) -> JSONResponse:
    file_id = request.path_params["file_id"]
    body = await request.json()
    result = await google_docs_convert_advanced(
        file_id=file_id,
        output_format=body.get("output_format", "doc"),
        output_path=body.get("output_path", ""),
    )
    status = 200 if result.get("success") else 400
    return JSONResponse(result, status_code=status)


async def api_document_export(request: Request) -> Response:
    """Stream a Google Doc export straight to the browser as a download.

    Reuses the `google_drive` tool's export operation (writes to a temp file,
    then this handler reads it back and cleans up) rather than duplicating
    the Drive API export call — the webapp and the MCP tool surface share
    exactly one code path.
    """
    file_id = request.path_params["file_id"]
    export_format = request.query_params.get("format", "pdf")
    if export_format not in _EXPORT_MIME_MAP:
        return JSONResponse({"error": f"unsupported format '{export_format}'"}, status_code=400)
    fmt = cast("ExportFormat", export_format)

    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / f"export.{fmt}"
        result = await google_drive(
            operation="export", file_id=file_id, export_format=fmt, output_path=str(dest)
        )
        if not result.get("success"):
            status = 404 if result.get("error_type") == "not_found" else 400
            return JSONResponse(result, status_code=status)
        data = dest.read_bytes()

    return Response(
        content=data,
        media_type=_EXPORT_MIME_MAP[fmt],
        headers={"Content-Disposition": f'attachment; filename="{file_id}.{fmt}"'},
    )


async def api_document_import(request: Request) -> JSONResponse:
    """Upload a local file (multipart/form-data) and convert it into a Google Doc."""
    form = await request.form()
    upload = form.get("file")
    if not isinstance(upload, UploadFile):
        return JSONResponse(
            {"success": False, "error": "file is required", "error_type": "validation"}, status_code=400
        )

    def _form_str(key: str) -> str | None:
        value = form.get(key)
        return value if isinstance(value, str) and value else None

    name = _form_str("name")
    folder_id = _form_str("folder_id")
    suffix = Path(upload.filename or "upload").suffix

    with tempfile.TemporaryDirectory() as tmp:
        dest = Path(tmp) / f"upload{suffix}"
        dest.write_bytes(await upload.read())
        result = await google_drive(
            operation="import_file", file_path=str(dest), name=name, folder_id=folder_id
        )

    status = 200 if result.get("success") else 400
    return JSONResponse(result, status_code=status)


async def _probe_app(client: httpx.AsyncClient, name: str, port: int) -> dict[str, Any] | None:
    try:
        resp = await client.get(f"http://127.0.0.1:{port}/", timeout=0.6)
        if resp.status_code >= 500:
            return None
    except httpx.HTTPError:
        return None
    return {"name": name, "port": port, "url": f"http://127.0.0.1:{port}/"}


async def api_apps(_request: Request) -> JSONResponse:
    """Dynamic fleet discovery — probe other frontends registered in WEBAPP_PORTS.md.

    Fleet-specific (see module-level _WEBAPP_PORTS_MD comment): returns an
    explicit `available: false` rather than an error when the shared registry
    isn't on disk, so this never looks like a broken feature on a non-fleet
    checkout of this repo.
    """
    if not _WEBAPP_PORTS_MD.is_file():
        return JSONResponse({"available": False, "items": []})

    frontends: dict[int, str] = {}
    for line in _WEBAPP_PORTS_MD.read_text(encoding="utf-8", errors="ignore").splitlines():
        m = _PORT_ROW_RE.match(line)
        if not m:
            continue
        port_str, repo, desc = m.groups()
        if "frontend" not in desc.lower():
            continue
        port = int(port_str)
        if port == settings.backend_port + 1:
            continue  # skip ourselves — no point linking to the page you're already on
        frontends[port] = repo

    limits = httpx.Limits(max_connections=60)
    async with httpx.AsyncClient(limits=limits) as client:
        results = await asyncio.gather(*(_probe_app(client, repo, port) for port, repo in frontends.items()))

    items = sorted((r for r in results if r), key=lambda r: r["name"])
    return JSONResponse({"available": True, "items": items})


async def api_logs(_request: Request) -> JSONResponse:
    return JSONResponse({"items": _LOG_BUFFER[-200:]})


async def api_sync_status(_request: Request) -> JSONResponse:
    result = await google_docs_sync(operation="status")
    result["data"]["last_run"] = _last_sync_result
    result["data"]["last_error"] = _last_sync_error
    return JSONResponse(result)


async def api_sync_configure(request: Request) -> JSONResponse:
    body = await request.json()
    result = await google_docs_sync(
        operation="configure",
        local_dir=body.get("local_dir"),
        folder_id=body.get("folder_id"),
        interval_seconds=int(body.get("interval_seconds", 300)),
        export_format=body.get("export_format", "docx"),
    )
    status = 200 if result.get("success") else 400
    return JSONResponse(result, status_code=status)


async def api_sync_enable(_request: Request) -> JSONResponse:
    result = await google_docs_sync(operation="enable")
    status = 200 if result.get("success") else 400
    return JSONResponse(result, status_code=status)


async def api_sync_disable(_request: Request) -> JSONResponse:
    result = await google_docs_sync(operation="disable")
    return JSONResponse(result)


async def api_sync_run_once(_request: Request) -> JSONResponse:
    global _last_sync_result, _last_sync_error
    result = await google_docs_sync(operation="run_once")
    if result.get("success"):
        _last_sync_result = result["data"]
        _last_sync_error = None
    else:
        _last_sync_error = result.get("error")
    status = 200 if result.get("success") else 400
    return JSONResponse(result, status_code=status)


async def _background_sync_pass() -> None:
    """One pass on the background poll timer — never raises, always logged."""
    global _last_sync_result, _last_sync_error
    config = load_sync_config(sync_config_path())
    if not config.enabled or not config.local_dir:
        return
    try:
        service = get_drive_service()
    except (NotConfiguredError, NotAuthenticatedError):
        return  # not ready yet — silently skip until the user finishes onboarding
    try:
        result = await run_sync_pass(
            service,
            local_dir=Path(config.local_dir),
            folder_id=config.folder_id,
            manifest_path=sync_manifest_path(),
            export_format=config.export_format,
        )
        _last_sync_result = result.as_dict()
        _last_sync_error = None
        logger.info("Background sync pass: %s", _last_sync_result)
    except Exception as exc:  # a bad pass must never kill the loop
        _last_sync_error = str(exc)
        logger.exception("Background sync pass failed")


async def _sync_loop() -> None:
    while True:
        await _background_sync_pass()
        config = load_sync_config(sync_config_path())
        interval = max(60, config.interval_seconds)
        await asyncio.sleep(interval)


@contextlib.asynccontextmanager
async def lifespan(app: Starlette):
    async with mcp_http_app.lifespan(app):
        task = asyncio.create_task(_sync_loop())
        try:
            yield
        finally:
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task


app = Starlette(
    routes=[
        Route("/api/health", api_health),
        Route("/api/capabilities", api_capabilities),
        Route("/api/dashboard", api_dashboard),
        Route("/api/tools", api_tools),
        Route("/api/skills", api_skills),
        Route("/api/skills/{name}", api_skill_content),
        Route("/skill/{name}", get_skill),
        Route("/api/auth/status", api_auth_status),
        Route("/api/auth/start", api_auth_start, methods=["POST"]),
        Route("/api/auth/revoke", api_auth_revoke, methods=["POST"]),
        Route("/api/onboarding/client", api_onboarding_client, methods=["POST"]),
        Route("/api/onboarding/client", api_onboarding_client_clear, methods=["DELETE"]),
        Route("/api/llm/providers", api_llm_providers),
        Route("/api/llm/models", api_llm_models),
        Route("/api/llm/chat", api_llm_chat, methods=["POST"]),
        Route("/api/documents", api_documents),
        Route("/api/documents/browse", api_documents_browse),
        Route("/api/documents/backup", api_documents_backup, methods=["POST"]),
        Route("/api/documents/import", api_document_import, methods=["POST"]),
        Route("/api/documents/{file_id}/export", api_document_export),
        Route("/api/documents/{file_id}/restore", api_document_restore, methods=["POST"]),
        Route("/api/documents/{file_id}/convert-advanced", api_document_convert_advanced, methods=["POST"]),
        Route("/api/apps", api_apps),
        Route("/api/logs", api_logs),
        Route("/api/sync/status", api_sync_status),
        Route("/api/sync/configure", api_sync_configure, methods=["POST"]),
        Route("/api/sync/enable", api_sync_enable, methods=["POST"]),
        Route("/api/sync/disable", api_sync_disable, methods=["POST"]),
        Route("/api/sync/run-once", api_sync_run_once, methods=["POST"]),
        Mount("/mcp", app=mcp_http_app),
    ],
    # Our own lifespan wraps mcp_http_app's (StreamableHTTPSessionManager lifespan
    # MUST still be forwarded to the parent app — fastmcp 3.4.4 lifespan pitfall,
    # see fastmcp/3.4-features.md) AND starts/stops the background sync poll loop.
    lifespan=lifespan,
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=[
                "http://localhost:11973",
                "http://127.0.0.1:11973",
                "tauri://localhost",
                "https://tauri.localhost",
            ],
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        )
    ],
)
