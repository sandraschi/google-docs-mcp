"""Prefab UI sync status card — in-chat rich view of `google_docs_sync(operation="status")`.

Per TOOL_DESIGN_STANDARDS.md §4.4's coverage rule, any tool that primarily reports status MUST
ship a Prefab surface in addition to the plain-dict tool.
"""

from __future__ import annotations

from fastmcp.server.server import ToolResult
from prefab_ui import PrefabApp
from prefab_ui.components import Badge, Heading, Row

from google_docs_mcp.tools.sync_tool import google_docs_sync


async def show_google_docs_sync_status_app() -> ToolResult:
    """Show the local-folder <-> Drive-folder sync configuration and status as a rich Prefab card.

    ## Return Format
    ToolResult with a PrefabApp status card and a plain-text `content` fallback for hosts that do
    not render MCP Apps. Same underlying data as `google_docs_sync(operation="status")`. Bounded
    output (fixed set of config fields + a tracked-doc count) — no pagination needed.

    ## Examples
    ```python
    await show_google_docs_sync_status_app()
    ```
    """
    result = await google_docs_sync(operation="status")
    config = result.get("data", {}).get("config", {})
    tracked_count = result.get("data", {}).get("tracked_count", 0)

    with PrefabApp(title="google-docs-mcp Sync") as app:
        Heading("Local Folder Mirror")
        Row(label="Local folder", value=config.get("local_dir") or "(not configured)")
        Row(label="Drive folder", value=config.get("folder_id") or "My Drive (root)")
        Row(label="Poll interval", value=f"{config.get('interval_seconds', 0)}s")
        Row(label="Local file format", value=config.get("export_format", "docx"))
        Row(label="Docs tracked", value=str(tracked_count))
        if not config.get("local_dir"):
            Badge("Not configured — call operation='configure'", variant="destructive")
        elif config.get("enabled"):
            Badge("Background sync enabled", variant="success")
        else:
            Badge("Configured, background sync off", variant="warning")

    summary = (
        f"Sync {'enabled' if config.get('enabled') else 'disabled'}, {tracked_count} doc(s) tracked."
        if config.get("local_dir")
        else "Sync not configured yet."
    )
    return ToolResult(content=summary, structured_content=app)
