"""Unit tests for the live-env Settings object."""

from __future__ import annotations

import sys

from google_docs_mcp.config import REPO_ROOT, data_dir, settings


def test_not_configured_by_default(monkeypatch, tmp_path):
    monkeypatch.delenv("GOOGLE_DOCS_MCP_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_DOCS_MCP_CLIENT_SECRET", raising=False)
    # Neutralize the local-client-file fallback: on a real workstation it may
    # hold credentials that would otherwise keep is_configured True (and, in
    # test_auth_tool, launch a real browser OAuth flow and hang the suite).
    monkeypatch.setenv("GOOGLE_DOCS_MCP_LOCAL_CONFIG_PATH", str(tmp_path / "none.json"))
    assert settings.is_configured is False


def test_configured_when_both_env_vars_set(monkeypatch):
    monkeypatch.setenv("GOOGLE_DOCS_MCP_CLIENT_ID", "x")
    monkeypatch.setenv("GOOGLE_DOCS_MCP_CLIENT_SECRET", "y")
    assert settings.is_configured is True


def test_partial_config_is_not_configured(monkeypatch, tmp_path):
    monkeypatch.setenv("GOOGLE_DOCS_MCP_CLIENT_ID", "x")
    monkeypatch.delenv("GOOGLE_DOCS_MCP_CLIENT_SECRET", raising=False)
    monkeypatch.setenv("GOOGLE_DOCS_MCP_LOCAL_CONFIG_PATH", str(tmp_path / "none.json"))
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


def test_data_dir_defaults_to_repo_root_in_dev(monkeypatch):
    monkeypatch.delenv("GOOGLE_DOCS_MCP_DATA_DIR", raising=False)
    monkeypatch.setattr(sys, "frozen", False, raising=False)
    assert data_dir() == REPO_ROOT / "data"


def test_data_dir_uses_localappdata_when_frozen(monkeypatch, tmp_path):
    # A naive REPO_ROOT/data default would resolve inside PyInstaller's
    # per-launch _MEIPASS temp extraction dir in the real frozen app — wiped
    # on exit, silently losing the saved OAuth client and token every close.
    monkeypatch.delenv("GOOGLE_DOCS_MCP_DATA_DIR", raising=False)
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert data_dir() == tmp_path / "com.sandraschi.google-docs-mcp" / "data"


def test_data_dir_env_override_wins_even_when_frozen(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setenv("GOOGLE_DOCS_MCP_DATA_DIR", str(tmp_path / "custom"))
    assert data_dir() == tmp_path / "custom"


def test_token_path_and_local_config_path_follow_data_dir(monkeypatch, tmp_path):
    monkeypatch.delenv("GOOGLE_DOCS_MCP_TOKEN_PATH", raising=False)
    monkeypatch.delenv("GOOGLE_DOCS_MCP_LOCAL_CONFIG_PATH", raising=False)
    monkeypatch.setenv("GOOGLE_DOCS_MCP_DATA_DIR", str(tmp_path))
    assert settings.token_path == tmp_path / "token.json"
    assert settings.local_config_path == tmp_path / "oauth_client.json"
