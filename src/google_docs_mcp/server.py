"""FastMCP server entry point — dual transport (stdio for Claude Desktop,
HTTP for the webapp backend to mount at /mcp).

No local database or long-running state — Google Docs/Drive are the source
of truth and the OAuth token cache is a single small file, so this server
skips the HTTP-daemon + stdio-proxy pattern from SOTA_REQUIREMENTS.md §2.3
("When NOT to probe: ... single-client servers that never run a 24/7 HTTP
daemon"). See docs/ARCHITECTURE.md for the full rationale.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastmcp import FastMCP
from fastmcp.server.providers.skills import SkillsDirectoryProvider

from google_docs_mcp import __version__
from google_docs_mcp.config import settings
from google_docs_mcp.tools.auth_tool import google_docs_auth
from google_docs_mcp.tools.browse_app import show_google_drive_folder_app
from google_docs_mcp.tools.docs_tool import google_docs
from google_docs_mcp.tools.drive_tool import google_drive
from google_docs_mcp.tools.help_tool import google_docs_mcp_help
from google_docs_mcp.tools.libreoffice_tool import google_docs_convert_advanced
from google_docs_mcp.tools.status_app import show_google_docs_status_app
from google_docs_mcp.tools.sync_status_app import show_google_docs_sync_status_app
from google_docs_mcp.tools.sync_tool import google_docs_sync

logger = logging.getLogger("google_docs_mcp")


@asynccontextmanager
async def lifespan(_app: FastMCP):
    """Shallow startup probe (SOTA_REQUIREMENTS §2.1): verify the token
    directory is writable and log the configuration state. Never blocks on
    a live Google API call — auth failures surface per-tool-call instead."""
    settings.token_path.parent.mkdir(parents=True, exist_ok=True)
    if settings.is_configured:
        logger.info("google-docs-mcp starting — OAuth client configured.")
    else:
        logger.warning(
            "google-docs-mcp starting — OAuth client NOT configured "
            "(GOOGLE_DOCS_MCP_CLIENT_ID/_SECRET unset). See docs/ONBOARDING.md."
        )
    yield


mcp = FastMCP(
    "google-docs-mcp",
    version=__version__,
    lifespan=lifespan,
)

# Annotation hints per TOOL_DESIGN_STANDARDS.md §9 — the fastmcp.tool.annotations
# constants module doesn't exist yet in 3.4.2, so these use the ToolAnnotations dict
# keys directly (readOnlyHint/destructiveHint/idempotentHint/openWorldHint). For a
# portmanteau mixing read/write/destructive operations, the tool-level hint reflects
# the worst case present (e.g. google_drive has delete_permanently -> destructiveHint=True).
mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True})(
    google_docs_auth
)
mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True})(google_docs)
mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": True, "openWorldHint": True})(google_drive)
mcp.tool(annotations={"readOnlyHint": True, "idempotentHint": True, "openWorldHint": False})(
    google_docs_mcp_help
)
mcp.tool(
    annotations={
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": True,
    }
)(google_docs_convert_advanced)
mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": False, "openWorldHint": True})(
    google_docs_sync
)
mcp.tool(app=True, annotations={"readOnlyHint": True, "idempotentHint": True, "openWorldHint": False})(
    show_google_docs_status_app
)
mcp.tool(app=True, annotations={"readOnlyHint": True, "idempotentHint": True, "openWorldHint": True})(
    show_google_drive_folder_app
)
mcp.tool(app=True, annotations={"readOnlyHint": True, "idempotentHint": True, "openWorldHint": False})(
    show_google_docs_sync_status_app
)


async def google_shutdown(confirmed: bool = False) -> str:
    """Shut down the google-docs-mcp server process.

    ## Return Format
    Confirmation prompt or termination notice string

    ## Examples
    ```python
    await google_shutdown(confirmed=True)
    ```
    """
    if not confirmed:
        return "Refusing: pass confirmed=true to terminate the google-docs-mcp server process."
    import os as _os
    import signal as _signal

    _os.kill(_os.getpid(), _signal.SIGTERM)
    return "google-docs-mcp server terminating."


mcp.tool(annotations={"readOnlyHint": False, "destructiveHint": True, "openWorldHint": False})(
    google_shutdown
)

_skills_dir = Path(__file__).resolve().parent / "skills"
if _skills_dir.is_dir():
    mcp.add_provider(SkillsDirectoryProvider(roots=[_skills_dir]))

# HTTP ASGI app — mounted at /mcp by the Starlette webapp backend. Its
# `.lifespan` MUST be passed to the parent app's constructor (FastMCP 3.4.4
# lifespan pitfall — see fastmcp/3.4-features.md).
mcp_http_app = mcp.http_app(path="/")


def main() -> None:
    """stdio entry point — what Claude Desktop / the .mcpb bundle launches."""
    logging.basicConfig(level=logging.INFO)
    mcp.run(show_banner=False)


if __name__ == "__main__":
    main()
