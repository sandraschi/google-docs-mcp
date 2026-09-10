# Architecture

## Overview

```
Claude Desktop (stdio) ──┐
                          ├──> FastMCP server (google_docs_mcp.server:mcp)
Webapp (HTTP, :11973) ────┘         │
   │  fetch /api/*                  ├── google_docs   (Docs API v1)
   ▼                                ├── google_drive  (Drive API v3)
Starlette backend (:11972)          ├── google_docs_auth (OAuth lifecycle)
   mounts mcp_http_app at /mcp      └── show_google_docs_status_app (Prefab)
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
