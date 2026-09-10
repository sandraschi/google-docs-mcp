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
