"""Unit tests for google_docs_auth."""

from __future__ import annotations

from google_docs_mcp.tools.auth_tool import google_docs_auth


async def test_status_unconfigured(monkeypatch):
    monkeypatch.delenv("GOOGLE_DOCS_MCP_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_DOCS_MCP_CLIENT_SECRET", raising=False)
    result = await google_docs_auth(operation="status")
    assert result["success"] is True
    assert result["data"]["configured"] is False
    assert result["data"]["authenticated"] is False


async def test_start_oauth_without_client_returns_not_configured(monkeypatch):
    monkeypatch.delenv("GOOGLE_DOCS_MCP_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_DOCS_MCP_CLIENT_SECRET", raising=False)
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
