"""Unit tests for the live-env Settings object."""

from __future__ import annotations

from google_docs_mcp.config import settings


def test_not_configured_by_default(monkeypatch):
    monkeypatch.delenv("GOOGLE_DOCS_MCP_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_DOCS_MCP_CLIENT_SECRET", raising=False)
    assert settings.is_configured is False


def test_configured_when_both_env_vars_set(monkeypatch):
    monkeypatch.setenv("GOOGLE_DOCS_MCP_CLIENT_ID", "x")
    monkeypatch.setenv("GOOGLE_DOCS_MCP_CLIENT_SECRET", "y")
    assert settings.is_configured is True


def test_partial_config_is_not_configured(monkeypatch):
    monkeypatch.setenv("GOOGLE_DOCS_MCP_CLIENT_ID", "x")
    monkeypatch.delenv("GOOGLE_DOCS_MCP_CLIENT_SECRET", raising=False)
    assert settings.is_configured is False


def test_default_backend_port_is_registered_in_webapp_ports(monkeypatch):
    monkeypatch.delenv("GOOGLE_DOCS_MCP_PORT", raising=False)
    assert settings.backend_port == 11972


def test_local_client_fallback_when_env_unset(monkeypatch, tmp_path):
    monkeypatch.delenv("GOOGLE_DOCS_MCP_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_DOCS_MCP_CLIENT_SECRET", raising=False)
    monkeypatch.setenv("GOOGLE_DOCS_MCP_LOCAL_CONFIG_PATH", str(tmp_path / "oauth_client.json"))

    assert settings.is_configured is False
    assert settings.client_source == "none"

    settings.write_local_client("wizard-id", "wizard-secret")
    assert settings.client_id == "wizard-id"
    assert settings.client_secret == "wizard-secret"
    assert settings.is_configured is True
    assert settings.client_source == "onboarding_wizard"

    assert settings.clear_local_client() is True
    assert settings.is_configured is False
    assert settings.clear_local_client() is False  # already gone


def test_env_vars_win_over_local_client_file(monkeypatch, tmp_path):
    monkeypatch.setenv("GOOGLE_DOCS_MCP_LOCAL_CONFIG_PATH", str(tmp_path / "oauth_client.json"))
    settings.write_local_client("wizard-id", "wizard-secret")
    monkeypatch.setenv("GOOGLE_DOCS_MCP_CLIENT_ID", "env-id")
    monkeypatch.setenv("GOOGLE_DOCS_MCP_CLIENT_SECRET", "env-secret")

    assert settings.client_id == "env-id"
    assert settings.client_secret == "env-secret"
    assert settings.client_source == "env"
