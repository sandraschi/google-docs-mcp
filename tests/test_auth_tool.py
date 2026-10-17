"""Unit tests for google_docs_auth."""

from __future__ import annotations

from google_docs_mcp.tools.auth_tool import google_docs_auth


async def test_status_unconfigured(monkeypatch, tmp_path):
    monkeypatch.delenv("GOOGLE_DOCS_MCP_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_DOCS_MCP_CLIENT_SECRET", raising=False)
    # Neutralize the local-client-file fallback (see test_config.py): without
    # this, a real workstation stays configured and start_oauth below would
    # open a REAL browser OAuth flow and hang the suite.
    monkeypatch.setenv("GOOGLE_DOCS_MCP_LOCAL_CONFIG_PATH", str(tmp_path / "none.json"))
    result = await google_docs_auth(operation="status")
    assert result["success"] is True
    assert result["data"]["configured"] is False
    assert result["data"]["authenticated"] is False


async def test_start_oauth_without_client_returns_not_configured(monkeypatch, tmp_path):
    monkeypatch.delenv("GOOGLE_DOCS_MCP_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_DOCS_MCP_CLIENT_SECRET", raising=False)
    monkeypatch.setenv("GOOGLE_DOCS_MCP_LOCAL_CONFIG_PATH", str(tmp_path / "none.json"))
    result = await google_docs_auth(operation="start_oauth")
    assert result["success"] is False
    assert result["error_type"] == "not_configured"


async def test_revoke_with_no_token_is_a_clean_noop(configured_env):
    result = await google_docs_auth(operation="revoke")
    assert result["success"] is True
    assert result["data"]["revoked"] is False


async def test_revoke_deletes_existing_token(configured_env):
    configured_env.token_path.parent.mkdir(parents=True, exist_ok=True)
    configured_env.token_path.write_text("{}", encoding="utf-8")
    result = await google_docs_auth(operation="revoke")
    assert result["success"] is True
    assert result["data"]["revoked"] is True
    assert not configured_env.token_path.exists()


async def test_unknown_operation(monkeypatch):
    result = await google_docs_auth(operation="bogus")  # type: ignore[arg-type]
    assert result["success"] is False
    assert result["error_type"] == "validation"


async def test_status_reports_weekly_grant_expiry(configured_env, monkeypatch):
    """invalid_grant on refresh (the weekly Testing-mode death) surfaces as
    grant_expired, not generic unauthenticated. Verified live 2026-10-17."""
    import json

    from google.auth.exceptions import RefreshError

    from google_docs_mcp import oauth

    configured_env.token_path.parent.mkdir(parents=True, exist_ok=True)
    configured_env.token_path.write_text(
        json.dumps(
            {
                "token": "dead",
                "refresh_token": "dead",
                "token_uri": "https://oauth2.googleapis.com/token",
                "client_id": "test-client-id.apps.googleusercontent.com",
                "client_secret": "test-client-secret",
                "scopes": oauth.settings.scopes,
                "expiry": "2020-01-01T00:00:00",
            }
        ),
        encoding="utf-8",
    )

    def _dead_refresh(self, request):
        raise RefreshError("invalid_grant: Token has been expired or revoked.")

    monkeypatch.setattr("google.oauth2.credentials.Credentials.refresh", _dead_refresh)
    result = await google_docs_auth(operation="status")
    assert result["success"] is True
    assert result["data"]["authenticated"] is False
    assert result["data"]["grant_expired"] is True
    assert "7 days" in result["message"]
