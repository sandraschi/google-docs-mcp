"""google_docs_auth — OAuth lifecycle portmanteau.

[RATIONALE] Authentication is not a Docs/Drive API concept — it is a
separate, stateful concern (browser consent, token cache) that both
`google_docs` and `google_drive` depend on. Isolating it into its own tiny
portmanteau keeps `start_oauth` (a "hands-on, opens your browser" operation)
clearly distinct from ordinary read/write tool calls, per the annotations
guidance in TOOL_DESIGN_STANDARDS.md §9.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Annotated, Any, Literal

from pydantic import Field

from google_docs_mcp import oauth

AuthOperation = Literal["status", "start_oauth", "revoke"]


async def google_docs_auth(
    operation: Annotated[
        AuthOperation,
        Field(
            description="'status' checks configuration/auth state (read-only). 'start_oauth' opens "
            "a browser consent screen and blocks until the user finishes or cancels. 'revoke' deletes "
            "the cached token, forcing re-consent next time."
        ),
    ],
) -> dict[str, Any]:
    """Check or perform Google OAuth authentication for Docs/Drive access.

    ## Operations
    - status — read-only: is the OAuth client configured, is a valid token cached, when does it expire
    - start_oauth — **opens the user's default browser** to Google's consent screen and blocks until
      the flow completes; on success the token is cached to `GOOGLE_DOCS_MCP_TOKEN_PATH`
    - revoke — deletes the cached token file (does not revoke server-side; forces re-consent locally)

    ## Return Format
    `{"success": true, "message": str, "data": {"configured": bool, "authenticated": bool,
    "scopes": [str], "token_path": str, "expiry": str | null}}` on success.
    `{"success": false, "error": str, "error_type": "not_configured", "suggestions": [str]}` when
    `start_oauth` is called before `GOOGLE_DOCS_MCP_CLIENT_ID`/`_SECRET` are set.

    ## Examples
    ```python
    await google_docs_auth(operation="status")
    await google_docs_auth(operation="start_oauth")
    await google_docs_auth(operation="revoke")
    ```

    Notes:
    - `start_oauth` MUST be presented to the user as "a browser window is about to open" before
      calling — it is a MUTATING, human-in-the-loop operation, not a silent background call.
    - See `docs/ONBOARDING.md` for how to create the Google Cloud OAuth client in the first place.
    """
    if operation == "status":
        status = oauth.get_status()
        return {
            "success": True,
            "message": "Authenticated." if status.authenticated else "Not authenticated.",
            "data": asdict(status),
        }

    if operation == "start_oauth":
        try:
            status = oauth.run_installed_app_flow()
        except oauth.NotConfiguredError as exc:
            return {
                "success": False,
                "error": str(exc),
                "error_type": "not_configured",
                "suggestions": ["See docs/ONBOARDING.md to create a Google Cloud OAuth client."],
            }
        return {
            "success": True,
            "message": "Authenticated successfully.",
            "data": asdict(status),
        }

    if operation == "revoke":
        removed = oauth.revoke()
        return {
            "success": True,
            "message": "Token revoked." if removed else "No cached token to revoke.",
            "data": {"revoked": removed},
        }

    return {"success": False, "error": f"Unknown operation '{operation}'", "error_type": "validation"}
