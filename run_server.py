"""PyInstaller entry point — HTTP transport for the Tauri desktop app.

Not used by Claude Desktop (which spawns the stdio entry point,
`google_docs_mcp.server:main`, via the normal `uv run google-docs-mcp`
console script). This file exists only so PyInstaller has a single,
importable script to freeze for the embedded Tauri backend, which always
runs the webapp's HTTP server (see docs/ARCHITECTURE.md).
"""

import os

import uvicorn

from google_docs_mcp.backend.app import app

if __name__ == "__main__":
    port = int(os.getenv("PORT", os.getenv("MCP_PORT", "11972")))
    host = os.getenv("HOST", os.getenv("MCP_HOST", "127.0.0.1"))
    uvicorn.run(app, host=host, port=port, log_level="info")
