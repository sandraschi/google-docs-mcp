"""Cross-server bridge to libreoffice-mcp — a real MCP client call, not a
shell-out or a reimplementation.

[RATIONALE] Google Drive's `files.export` (see `google_drive` operation
`export`) covers pdf/docx/odt/txt/html/rtf/epub adequately for most needs.
It does NOT cover legacy `.doc`, OpenDocument flat formats (`.fodt`), or give
any control over the conversion itself. Rather than reimplement document
conversion (a genuinely hard problem — LibreOffice's headless `soffice
--convert-to` already solves it), this module calls the fleet's own
libreoffice-mcp server as an MCP client, exactly the way Claude Desktop would
call it directly, just proxied through google-docs-mcp so the whole
"export from Drive, then convert with LibreOffice" workflow is one tool call.
"""

from __future__ import annotations

import os
from typing import Any

from fastmcp import Client

LIBREOFFICE_MCP_URL = os.getenv("LIBREOFFICE_MCP_URL", "http://127.0.0.1:10981/mcp")


class LibreOfficeUnavailableError(RuntimeError):
    """Raised when libreoffice-mcp isn't reachable at LIBREOFFICE_MCP_URL."""


async def convert_via_libreoffice(input_path: str, output_format: str) -> dict[str, Any]:
    """Call libreoffice-mcp's `libreoffice(operation="convert", ...)` tool.

    Returns the tool's own response dict verbatim:
    `{"success": bool, "message": str, "next_steps": [...],
      "data": {"success": bool, "output": str | None, "error": str | None, ...}}`
    — note the *inner* `data.output` is the produced file path; the outer
    `success`/`message` describe the MCP call itself succeeding, not
    necessarily that the conversion produced a file (check `data.success`).
    """
    try:
        async with Client(LIBREOFFICE_MCP_URL) as client:
            result = await client.call_tool(
                "libreoffice",
                {"operation": "convert", "input_path": input_path, "output_format": output_format},
            )
    except Exception as exc:  # connection refused, timeout, protocol error — all "unavailable"
        raise LibreOfficeUnavailableError(
            f"libreoffice-mcp not reachable at {LIBREOFFICE_MCP_URL}: {exc}"
        ) from exc

    if isinstance(result.data, dict):
        return result.data
    # Fallback: no output schema registered on the far end, data wasn't deserialized —
    # the text content still carries the same JSON, parsed defensively.
    import json

    for block in result.content:
        text = getattr(block, "text", None)
        if text:
            try:
                return json.loads(text)
            except (json.JSONDecodeError, TypeError):
                continue
    return {"success": False, "message": "Could not parse libreoffice-mcp response", "data": {}}
