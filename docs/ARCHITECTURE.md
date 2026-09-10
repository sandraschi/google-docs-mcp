# Architecture

## Overview

```
Claude Desktop (stdio) ──┐
                          ├──> FastMCP server (google_docs_mcp.server:mcp)
Webapp (HTTP, :11973) ────┘         │
   │  fetch /api/*                  ├── google_docs   (Docs API v1)
   ▼                                ├── google_drive  (Drive API v3)
Starlette backend (:11972)          ├── google_docs_auth (OAuth lifecycle)
   mounts mcp_http_app at /mcp      ├── google_docs_convert_advanced ──> libreoffice-mcp (MCP client call)
   + background sync poll loop     ├── google_docs_sync (sync_engine.py)
                                    └── show_google_docs_status_app (Prefab)
                                            │
                                            ▼
                                   Google OAuth2 + Docs/Drive REST APIs
```

- **No local database.** Google Docs/Drive are the source of truth for every document. The
  only local state is the cached OAuth token (`data/token.json`).
- **No HTTP-daemon + stdio-proxy pattern** (SOTA_REQUIREMENTS.md §2.3). That pattern exists to
  prevent multiple stdio clients from fighting over a local SQLite/LanceDB file. This server
  has no such file — every stdio instance talks directly to Google's API, and Google's API is
  already safe for concurrent access from multiple processes. Adding the daemon+proxy layer
  here would be speculative complexity with no problem to solve.
- **Dual transport**: `google_docs_mcp.server:mcp` runs over stdio for Claude Desktop
  (`google-docs-mcp` console script) and is also exposed as an ASGI sub-app
  (`mcp_http_app`) mounted at `/mcp` on the Starlette webapp backend, so the webapp's own
  Chat page can talk to the same tool surface over HTTP.

## Ports

| Service | Port | Registered in |
|---|---|---|
| Webapp backend (Starlette + `/mcp` mount) | 11972 | `mcp-central-docs/operations/WEBAPP_PORTS.md` |
| Webapp frontend (Vite dev server) | 11973 | same |

## Data flow — a typical edit

1. User: "Add a heading to my Q3 report."
2. Agent calls `google_drive(operation="search", query="Q3 report")` → gets `file_id`.
3. Agent calls `google_docs(operation="get_structure", document_id=file_id)` to find where the
   document currently starts (index 1 in a fresh doc).
4. Agent calls `google_docs(operation="insert_text", document_id=file_id, index=1, text="Q3 Report\n")`
   then `update_paragraph_style(..., named_style_type="HEADING_1")` over that range.
5. Every call is a direct HTTPS request from the user's machine to
   `docs.googleapis.com` / `www.googleapis.com`, authenticated with the cached OAuth token.

## OAuth flow

Installed-app (desktop) flow via `google-auth-oauthlib.flow.InstalledAppFlow.run_local_server()`
— a loopback HTTP server on an ephemeral (or configured) port receives the redirect after the
user consents in their browser. This is the only correct flow for a process that isn't a public
web server; see `docs/ONBOARDING.md` for the Cloud Console setup steps.

### OAuth client configuration — two sources

The OAuth client id/secret can come from either `GOOGLE_DOCS_MCP_CLIENT_ID`/`_SECRET`
environment variables (set via `claude_desktop_config.json`) **or** a local file,
`data/oauth_client.json`, written by the webapp's Onboarding wizard (`POST
/api/onboarding/client`) for people who never touch the Claude Desktop config directly. Env
vars always win when both are present — `config.py`'s `Settings.client_source` reports which
one is actually active. The file is gitignored and 0600 on POSIX (best-effort on Windows).

## Local folder mirror (sync)

`google_docs_sync` / `sync_engine.py` implement a **polling**, not push-based, two-way sync
between a local folder and a Drive folder. A true live sync (à la Google Drive Desktop or
OneDrive) needs either a publicly reachable HTTPS endpoint for Google's `files.watch` push
notifications or continuous local file-system watching tied to instant push — neither is
realistic for a local desktop app with no public endpoint. Instead, each pass compares Drive's
`modifiedTime` and a local SHA256 content hash against what was recorded at the last successful
sync (`data/sync_manifest.json`), and reconciles.

The Starlette backend's `lifespan` starts an `asyncio.create_task` background loop
(`_sync_loop`) alongside `mcp_http_app.lifespan` — it wakes every `interval_seconds` (min 60),
skips silently if not configured/authenticated, and never lets a bad pass kill the loop. State
(`sync_config.json`, `sync_manifest.json`) lives under `data/` by default but every path is
resolved live via `os.getenv()` (`sync_tool.sync_config_path()`/`sync_manifest_path()`) so tests
can isolate it without touching the real repo — same pattern as `config.Settings`.

Safety defaults: a doc changed on both sides is a **conflict** (local edit renamed with a
timestamp suffix and kept, Drive's version becomes canonical — never silently overwritten); a
doc trashed on Drive moves the local file to `_remote_deleted/` (never hard-deleted); a file
deleted locally self-heals by being re-pulled next pass (Drive is authoritative, never cascades
into deleting the Drive doc).

## LibreOffice cross-connect

`google_docs_convert_advanced` reaches format conversions Drive's native `export` can't produce
(`doc`, `fodt`, `rtf`) by making a genuine MCP-to-MCP client call to a sibling
[libreoffice-mcp](../../libreoffice-mcp) server (`libreoffice_bridge.py`, via FastMCP's `Client`
class — not a subprocess shell-out). It exports the doc to a temp docx through the existing
`google_drive(operation="export")` path, then calls libreoffice-mcp's `libreoffice(operation=
"convert")` tool. If libreoffice-mcp isn't reachable at `LIBREOFFICE_MCP_URL` (default
`http://127.0.0.1:10981/mcp`), the error surfaces as `error_type: "dependency_unavailable"` —
distinct from this server's own `not_configured`/`not_authenticated` — so callers can tell "you
haven't set up Google Docs MCP" apart from "the other server isn't running."

## Apps Hub (fleet discovery)

`GET /api/apps` is specific to Sandra's own `D:\Dev\repos` fleet layout: it reads the sibling
`mcp-central-docs/operations/WEBAPP_PORTS.md` registry, extracts every row whose description
contains "Frontend", and probes each port with a 0.6s timeout in parallel. On any machine
without that sibling repo, it returns `{"available": false, "items": []}` rather than erroring
— the webapp's Apps Hub page renders an explicit "not applicable here" message in that case.
