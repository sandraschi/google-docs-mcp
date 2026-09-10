"""Environment configuration for google-docs-mcp.

`settings` is a module-level object whose attributes are properties that
read `os.environ` on every access (not values frozen at import time). This
keeps `uv run google-docs-mcp` config correct in production (env vars are
set before import anyway) *and* makes `monkeypatch.setenv` work naturally in
tests without a fragile "recreate and rebind everywhere" dance.

OAuth client id/secret have a second source: `data/oauth_client.json`, a
local file the webapp's onboarding wizard can write to (POST
/api/onboarding/client) since a running process can't set its own future
environment variables. Env vars always win when both are present — the file
is a convenience for people using the webapp/desktop app who never touch
`claude_desktop_config.json` directly.
"""

from __future__ import annotations

import contextlib
import json
import os
import stat
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
    def local_config_path(self) -> Path:
        return Path(
            os.getenv("GOOGLE_DOCS_MCP_LOCAL_CONFIG_PATH", str(REPO_ROOT / "data" / "oauth_client.json"))
        )

    def _local_client(self) -> dict[str, str]:
        if not self.local_config_path.is_file():
            return {}
        try:
            data = json.loads(self.local_config_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    @property
    def client_id(self) -> str | None:
        return os.getenv("GOOGLE_DOCS_MCP_CLIENT_ID") or self._local_client().get("client_id") or None

    @property
    def client_secret(self) -> str | None:
        return os.getenv("GOOGLE_DOCS_MCP_CLIENT_SECRET") or self._local_client().get("client_secret") or None

    @property
    def client_source(self) -> str:
        """Where the currently-active client id/secret came from — for the Settings/onboarding UI."""
        if os.getenv("GOOGLE_DOCS_MCP_CLIENT_ID") and os.getenv("GOOGLE_DOCS_MCP_CLIENT_SECRET"):
            return "env"
        if self._local_client().get("client_id") and self._local_client().get("client_secret"):
            return "onboarding_wizard"
        return "none"

    def write_local_client(self, client_id: str, client_secret: str) -> None:
        """Persist client id/secret from the onboarding wizard. 0600 perms; gitignored."""
        self.local_config_path.parent.mkdir(parents=True, exist_ok=True)
        self.local_config_path.write_text(
            json.dumps({"client_id": client_id, "client_secret": client_secret}), encoding="utf-8"
        )
        # best-effort — Windows ACLs don't honor POSIX chmod bits the same way
        with contextlib.suppress(OSError):
            os.chmod(self.local_config_path, stat.S_IRUSR | stat.S_IWUSR)

    def clear_local_client(self) -> bool:
        if self.local_config_path.is_file():
            self.local_config_path.unlink()
            return True
        return False

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
