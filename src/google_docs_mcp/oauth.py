"""OAuth 2.0 credential lifecycle for Google Docs / Drive.

Uses the installed-app (desktop) flow — google-docs-mcp runs on the user's
own machine via Claude Desktop, so a loopback redirect is the correct flow
(never the web-server flow, which needs a public redirect URI).

Token storage: a single JSON file at `settings.token_path` (default
`data/token.json`, gitignored). Not encrypted at rest — same trust model as
`claude_desktop_config.json` itself. Document this in ONBOARDING.md.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow

from google_docs_mcp.config import settings

logger = logging.getLogger("google_docs_mcp.oauth")


class NotConfiguredError(RuntimeError):
    """Raised when GOOGLE_DOCS_MCP_CLIENT_ID / _SECRET are missing."""


class NotAuthenticatedError(RuntimeError):
    """Raised when no valid token exists and the caller must run start_oauth."""


@dataclass
class AuthStatus:
    configured: bool
    authenticated: bool
    scopes: list[str]
    token_path: str
    expiry: str | None = None


def _client_config() -> dict:
    if not settings.is_configured:
        raise NotConfiguredError(
            "GOOGLE_DOCS_MCP_CLIENT_ID / GOOGLE_DOCS_MCP_CLIENT_SECRET are not set. "
            "See docs/ONBOARDING.md to create a Google Cloud OAuth client."
        )
    return {
        "installed": {
            "client_id": settings.client_id,
            "client_secret": settings.client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": ["http://localhost"],
        }
    }


def load_credentials() -> Credentials | None:
    """Load cached credentials, refreshing an expired access token in place.

    Returns None when no token file exists yet. Raises NotConfiguredError if
    the OAuth client itself was never configured (nothing to refresh with).
    """
    if not settings.token_path.exists():
        return None
    if not settings.is_configured:
        raise NotConfiguredError(
            "A cached token exists but GOOGLE_DOCS_MCP_CLIENT_ID/_SECRET are unset — "
            "cannot refresh. Re-set the env vars or run start_oauth again."
        )

    data = json.loads(settings.token_path.read_text(encoding="utf-8"))
    creds = Credentials.from_authorized_user_info(data, settings.scopes)

    if creds and creds.expired and creds.refresh_token:
        try:
            creds.refresh(Request())
            _save_credentials(creds)
        except RefreshError as exc:
            logger.warning("Token refresh failed: %s", exc)
            return None

    return creds if creds and creds.valid else None


def _save_credentials(creds: Credentials) -> None:
    settings.token_path.parent.mkdir(parents=True, exist_ok=True)
    settings.token_path.write_text(creds.to_json(), encoding="utf-8")


def run_installed_app_flow(port: int | None = None) -> AuthStatus:
    """Run the interactive OAuth consent flow, opening the user's browser.

    This blocks until the user completes (or abandons) the browser consent
    screen — it is a "hands-on" tool call by design; the caller (agent) MUST
    tell the user a browser window is about to open.
    """
    flow = InstalledAppFlow.from_client_config(_client_config(), settings.scopes)
    creds = flow.run_local_server(port=port or settings.oauth_port, open_browser=True)
    _save_credentials(creds)
    return get_status()


def revoke() -> bool:
    """Delete the cached token file. Does not call Google's revoke endpoint
    (that requires the token to still be valid); deleting the local cache is
    sufficient to force re-consent on next use."""
    if settings.token_path.exists():
        settings.token_path.unlink()
        return True
    return False


def get_status() -> AuthStatus:
    configured = settings.is_configured
    creds: Credentials | None = None
    if configured:
        try:
            creds = load_credentials()
        except NotConfiguredError:
            creds = None
    expiry = None
    if creds and creds.expiry:
        expiry = creds.expiry.isoformat()
    return AuthStatus(
        configured=configured,
        authenticated=bool(creds and creds.valid),
        scopes=settings.scopes,
        token_path=str(settings.token_path),
        expiry=expiry,
    )


def require_credentials() -> Credentials:
    """Fetch valid credentials or raise a caller-friendly error."""
    if not settings.is_configured:
        raise NotConfiguredError(
            "GOOGLE_DOCS_MCP_CLIENT_ID / GOOGLE_DOCS_MCP_CLIENT_SECRET are not set. "
            "See docs/ONBOARDING.md to create a Google Cloud OAuth client."
        )
    creds = load_credentials()
    if creds is None:
        raise NotAuthenticatedError(
            "Not authenticated. Call google_docs_auth(operation='start_oauth') first, "
            "or see docs/ONBOARDING.md."
        )
    return creds
