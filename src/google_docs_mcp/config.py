"""Environment configuration for google-docs-mcp.

`settings` is a module-level object whose attributes are properties that
read `os.environ` on every access (not values frozen at import time). This
keeps `uv run google-docs-mcp` config correct in production (env vars are
set before import anyway) *and* makes `monkeypatch.setenv` work naturally in
tests without a fragile "recreate and rebind everywhere" dance.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

DEFAULT_SCOPES = [
    "https://www.googleapis.com/auth/documents",
    "https://www.googleapis.com/auth/drive",
]


def _env_bool(name: str, default: bool) -> bool:
    val = os.getenv(name)
    if val is None:
        return default
    return val.strip().lower() in {"1", "true", "yes", "on"}


class Settings:
    """Live view over environment variables — every property re-reads os.environ."""

    @property
    def client_id(self) -> str | None:
        return os.getenv("GOOGLE_DOCS_MCP_CLIENT_ID") or None

    @property
    def client_secret(self) -> str | None:
        return os.getenv("GOOGLE_DOCS_MCP_CLIENT_SECRET") or None

    @property
    def token_path(self) -> Path:
        return Path(os.getenv("GOOGLE_DOCS_MCP_TOKEN_PATH", str(REPO_ROOT / "data" / "token.json")))

    @property
    def scopes(self) -> list[str]:
        return list(DEFAULT_SCOPES)

    @property
    def oauth_port(self) -> int:
        return int(os.getenv("GOOGLE_DOCS_MCP_OAUTH_PORT", "0"))

    @property
    def backend_host(self) -> str:
        return os.getenv("GOOGLE_DOCS_MCP_HOST", "127.0.0.1")

    @property
    def backend_port(self) -> int:
        return int(os.getenv("GOOGLE_DOCS_MCP_PORT", "11972"))

    @property
    def prefab_apps_enabled(self) -> bool:
        return _env_bool("GOOGLE_DOCS_MCP_PREFAB_APPS", True)

    @property
    def http_daemon_url(self) -> str:
        return os.getenv("SERVER_API_URL", "http://127.0.0.1:11972")

    @property
    def is_configured(self) -> bool:
        """True once both OAuth client id and secret are present.

        This does NOT mean a valid token exists yet — see auth status tool.
        """
        return bool(self.client_id and self.client_secret)


settings = Settings()
