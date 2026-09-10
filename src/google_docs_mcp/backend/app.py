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

import logging
from dataclasses import asdict
from pathlib import Path
from typing import Any

import httpx
from starlette.applications import Starlette
from starlette.concurrency import run_in_threadpool
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Mount, Route

from google_docs_mcp import __version__, oauth
from google_docs_mcp.server import mcp, mcp_http_app
from google_docs_mcp.tools.drive_tool import google_drive

logger = logging.getLogger("google_docs_mcp.backend")

_SKILLS_DIR = Path(__file__).resolve().parents[1] / "skills"

_LOCAL_PROVIDERS = [
    {"name": "Ollama", "port": 11434, "probe": "/api/tags", "kind": "ollama"},
    {"name": "LM Studio", "port": 1234, "probe": "/v1/models", "kind": "openai-compat"},
    {"name": "vLLM", "port": 8000, "probe": "/v1/models", "kind": "openai-compat"},
]

_LOG_BUFFER: list[str] = []


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
    provider = request.query_params.get("provider", "").lower()
    match = next((p for p in _LOCAL_PROVIDERS if p["name"].lower() == provider), None)
    if not match:
        return JSONResponse({"models": [], "error": f"unknown provider '{provider}'"}, status_code=400)
    base = f"http://127.0.0.1:{match['port']}"
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{base}{match['probe']}", timeout=3.0)
            data = resp.json()
    except httpx.HTTPError:
        return JSONResponse({"models": []})
    if match["kind"] == "ollama":
        models = [m["name"] for m in data.get("models", [])]
    else:
        models = [m["id"] for m in data.get("data", [])]
    return JSONResponse({"models": models})


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


async def api_logs(_request: Request) -> JSONResponse:
    return JSONResponse({"items": _LOG_BUFFER[-200:]})


app = Starlette(
    routes=[
        Route("/api/health", api_health),
        Route("/api/dashboard", api_dashboard),
        Route("/api/tools", api_tools),
        Route("/api/skills", api_skills),
        Route("/api/skills/{name}", api_skill_content),
        Route("/skill/{name}", get_skill),
        Route("/api/auth/status", api_auth_status),
        Route("/api/auth/start", api_auth_start, methods=["POST"]),
        Route("/api/auth/revoke", api_auth_revoke, methods=["POST"]),
        Route("/api/llm/providers", api_llm_providers),
        Route("/api/llm/models", api_llm_models),
        Route("/api/llm/chat", api_llm_chat, methods=["POST"]),
        Route("/api/documents", api_documents),
        Route("/api/logs", api_logs),
        Mount("/mcp", app=mcp_http_app),
    ],
    # StreamableHTTPSessionManager lifespan MUST be forwarded to the parent app
    # (fastmcp 3.4.4 lifespan pitfall — see fastmcp/3.4-features.md).
    lifespan=mcp_http_app.lifespan,
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
