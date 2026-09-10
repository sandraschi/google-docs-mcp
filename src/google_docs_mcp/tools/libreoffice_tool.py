"""google_docs_convert_advanced — bridges to libreoffice-mcp for formats and
conversion fidelity Google Drive's own export doesn't cover.

[RATIONALE] Splitting this from `google_drive`'s `export` operation is
deliberate, not tool sprawl: `export` calls Google's own conversion
(`files.export`), a single well-understood API boundary. This tool calls a
*different* MCP server (libreoffice-mcp) over the network, has a different
availability story (it can be "not running" independently of Google's own
uptime), and chains two operations (export from Drive, then convert with
LibreOffice) rather than one. Folding it into `google_drive` would blur what
`error_type: "dependency_unavailable"` even means for that tool's other 20
operations, which have no such external dependency.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from typing import Annotated, Any, Literal

from pydantic import Field

from google_docs_mcp.libreoffice_bridge import LibreOfficeUnavailableError, convert_via_libreoffice
from google_docs_mcp.tools.drive_tool import google_drive

AdvancedFormat = Literal["doc", "fodt", "rtf", "odt", "txt", "pdf", "html"]


async def google_docs_convert_advanced(
    file_id: Annotated[str, Field(description="Google Doc id to convert.")],
    output_format: Annotated[
        AdvancedFormat,
        Field(
            description="Target format, produced by LibreOffice's converter instead of Drive's own "
            "export. Use this for formats google_drive's 'export' operation doesn't offer — "
            "notably legacy 'doc' and OpenDocument flat-XML 'fodt'."
        ),
    ],
    output_path: Annotated[str, Field(description="Local path to write the converted file to.")],
) -> dict[str, Any]:
    """Export a Google Doc, then convert it with libreoffice-mcp (a real MCP-to-MCP call).

    ## Return Format
    `{"success": true, "message": str, "data": {"output_path": str, "format": str}}` on success.
    On failure: `{"success": false, "error": str, "error_type": str, "suggestions": [str]}` —
    `error_type` is `"dependency_unavailable"` specifically when libreoffice-mcp itself can't be
    reached (distinct from this server's own `not_configured`/`not_authenticated`/etc.), plus the
    usual `google_drive` error types for the export half of this operation.

    ## Examples
    ```python
    await google_docs_convert_advanced(file_id="1AbC...", output_format="doc",
                                        output_path="C:/Users/me/Downloads/legacy.doc")
    ```

    Notes:
    - Requires **libreoffice-mcp running** (its backend, not necessarily its webapp) — start it the
      same way any other fleet MCP server starts. If it's not reachable, this returns a clear
      `dependency_unavailable` error rather than hanging.
    - Prefer `google_drive(operation="export", ...)` for pdf/docx/odt/txt/html/rtf/epub — it has no
      external dependency and is faster (no intermediate export + second process).
    """
    with tempfile.TemporaryDirectory() as tmp:
        intermediate = Path(tmp) / "source.docx"
        export_result = await google_drive(
            operation="export", file_id=file_id, export_format="docx", output_path=str(intermediate)
        )
        if not export_result.get("success"):
            return export_result

        try:
            lo_response = await convert_via_libreoffice(str(intermediate), output_format)
        except LibreOfficeUnavailableError as exc:
            return {
                "success": False,
                "error": str(exc),
                "error_type": "dependency_unavailable",
                "suggestions": [
                    "Start libreoffice-mcp (its backend, port 10981) and retry.",
                    "Or use google_drive(operation='export', export_format=...) for formats it "
                    "already covers (pdf/docx/odt/txt/html/rtf/epub) — no external dependency.",
                ],
            }

        inner = lo_response.get("data", {}) if isinstance(lo_response, dict) else {}
        if not lo_response.get("success") or not inner.get("success"):
            return {
                "success": False,
                "error": inner.get("error") or lo_response.get("message") or "LibreOffice conversion failed",
                "error_type": "api_error",
                "data": lo_response,
            }

        produced_path = inner.get("output")
        if not produced_path:
            return {
                "success": False,
                "error": "libreoffice-mcp reported success but no output path",
                "error_type": "api_error",
                "data": lo_response,
            }

        dest = Path(output_path)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(produced_path, dest)

    return {
        "success": True,
        "message": f"Converted via LibreOffice to {dest} ({output_format}).",
        "data": {"output_path": str(dest), "format": output_format},
    }
