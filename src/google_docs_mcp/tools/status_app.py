"""Prefab UI status card — in-chat rich view of auth/config state.

Per SOTA_REQUIREMENTS.md §2.2, any tool whose job is primarily status/health
MUST ship a Prefab surface, not only a plain dict. This mirrors the reference
pattern in multi-backup-mcp/src/multi_backup_mcp/tools/prefab_cards.py.
"""

from __future__ import annotations

from fastmcp.tools.base import ToolResult  # canonical home (BUG-059)
from prefab_ui import PrefabApp
from prefab_ui.components import Badge, Text
from prefab_ui.components import Heading as _Heading

from google_docs_mcp import __version__, oauth


def Heading(text: str, **kwargs) -> _Heading:  # noqa: N802 - compat shim (prefab-ui 0.20 made content keyword-only)
    """Positional-text shim; drop if prefab-ui ever restores positional content."""
    return _Heading(content=text, **kwargs)


def Row(label: str, value: str = "", **kwargs) -> Text:  # noqa: N802 - compat shim (0.20 Row takes children only)
    """Two-arg row shim."""
    return Text(f"{label}: {value}".strip(": ").strip())


async def show_google_docs_status_app() -> ToolResult:
    """Show OAuth configuration and authentication state as a rich Prefab card.

    ## Return Format
    ToolResult with a PrefabApp status card and a plain-text `content` fallback for hosts
    that do not render MCP Apps. Bounded output (fixed set of fields) — no pagination needed.

    ## Examples
    ```python
    await show_google_docs_status_app()
    ```
    """
    status = oauth.get_status()

    with PrefabApp(title="google-docs-mcp Status") as app:
        Heading("Google Docs / Drive Connection")
        Row(label="Version", value=__version__)
        Row(label="OAuth client configured", value="Yes" if status.configured else "No")
        Row(label="Authenticated", value="Yes" if status.authenticated else "No")
        Row(label="Token path", value=status.token_path)
        if status.expiry:
            Row(label="Token expiry", value=status.expiry)
        if status.authenticated:
            Badge("Connected", variant="success")
        elif status.configured:
            Badge("Not authenticated — run start_oauth", variant="warning")
        else:
            Badge("Not configured — see ONBOARDING.md", variant="destructive")

    summary = (
        f"google-docs-mcp v{__version__} — "
        f"{'authenticated' if status.authenticated else 'not authenticated'} "
        f"({'configured' if status.configured else 'not configured'})"
    )
    return ToolResult(content=summary, structured_content=app)
