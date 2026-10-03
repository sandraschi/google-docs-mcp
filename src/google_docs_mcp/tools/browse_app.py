"""Prefab UI folder browser card — in-chat rich view of `google_drive(operation="browse")`.

Per TOOL_DESIGN_STANDARDS.md §4.4's coverage rule, any tool that primarily lists items MUST
ship a Prefab surface in addition to the plain-dict tool. This is that surface for `browse` —
`google_drive(operation="browse", ...)` itself stays a thin dict tool for programmatic/agent
use; this dedicated tool adds the rich card.
"""

from __future__ import annotations

from typing import Annotated

from fastmcp.tools.base import ToolResult  # canonical home (BUG-059)
from prefab_ui import PrefabApp
from prefab_ui.components import Badge, DataTable, DataTableColumn, Text
from prefab_ui.components import Heading as _Heading
from pydantic import Field

from google_docs_mcp.tools.drive_tool import google_drive


def Heading(text: str, **kwargs) -> _Heading:  # noqa: N802 - compat shim (prefab-ui 0.20 made content keyword-only)
    """Positional-text shim; drop if prefab-ui ever restores positional content."""
    return _Heading(content=text, **kwargs)


def Row(label: str, value: str = "", **kwargs) -> Text:  # noqa: N802 - compat shim (0.20 Row takes children only)
    """Two-arg row shim."""
    return Text(f"{label}: {value}".strip(": ").strip())


async def show_google_drive_folder_app(
    folder_id: Annotated[
        str | None,
        Field(description="Drive folder to browse (omit/None for Drive root)."),
    ] = None,
) -> ToolResult:
    """Show a Drive folder's contents (subfolders + Google Docs) as a rich Prefab card.

    ## Return Format
    ToolResult with a PrefabApp card and a plain-text `content` fallback for hosts that do not
    render MCP Apps. Same underlying data as `google_drive(operation="browse", folder_id=...)`
    — this tool exists for the in-chat rich presentation, not as a second way to fetch the data
    programmatically. Bounded per `browse`'s own pagination (see that tool's docstring); this
    card shows the current page only, no "load more" control.

    ## Examples
    ```python
    await show_google_drive_folder_app()
    await show_google_drive_folder_app(folder_id="1AbCdEfGhIjK...")
    ```
    """
    result = await google_drive(operation="browse", folder_id=folder_id)

    if not result.get("success"):
        with PrefabApp(title="Google Drive Folder") as app:
            Heading("Google Drive")
            Badge(result.get("error", "Unavailable"), variant="destructive")
            Row(label="error_type", value=result.get("error_type", "unknown"))
        return ToolResult(
            content=f"Could not browse Drive: {result.get('error', 'unknown error')}",
            structured_content=app,
        )

    data = result.get("data", {})
    current = data.get("folder")
    breadcrumbs = data.get("breadcrumbs", [])
    folders = data.get("folders", [])
    files = data.get("files", [])

    crumb_path = " / ".join(["My Drive"] + [b["name"] for b in breadcrumbs]) or "My Drive"

    with PrefabApp(title=f"Drive: {current['name'] if current else 'My Drive'}") as app:
        Heading(crumb_path)
        Row(label="Folders", value=str(len(folders)))
        Row(label="Docs (this page)", value=str(len(files)))
        if data.get("has_more"):
            Badge("More docs available — pass next_cursor to see them", variant="warning")

        if folders:
            DataTable(
                columns=[DataTableColumn(key="name", header="Folder", sortable=True)],
                rows=[{"name": f["name"]} for f in folders],
            )
        if files:
            DataTable(
                columns=[
                    DataTableColumn(key="name", header="Document", sortable=True),
                    DataTableColumn(key="modifiedTime", header="Modified", sortable=True),
                ],
                rows=[{"name": f["name"], "modifiedTime": f.get("modifiedTime", "")} for f in files],
            )
        if not folders and not files:
            Badge("Empty folder", variant="secondary")

    summary = f"{crumb_path}: {len(folders)} folder(s), {len(files)} doc(s)."
    return ToolResult(content=summary, structured_content=app)
