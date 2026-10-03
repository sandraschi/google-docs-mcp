"""Shared pytest fixtures.

Declared doubles (see docs/DEVELOPMENT.md § Declared doubles / TESTING_GUIDE.md):
- `configured_env` fakes OAuth env vars so `settings.is_configured` is True
  without a real Google Cloud client.
- `mock_docs_service` / `mock_drive_service` are `unittest.mock.MagicMock`
  stand-ins for `googleapiclient.discovery.Resource`, patched in place of
  `get_docs_service` / `get_drive_service` — no real network call is made,
  ever, in the unit test suite.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.fixture(autouse=True)
def _neutralize_local_oauth_client(monkeypatch, tmp_path):
    """Point the local-client fallback at a nonexistent file for every test.

    `Settings._local_client()` reads a real workstation file that can keep
    `is_configured` True despite deleted env vars — on 2026-10-02 this let
    `start_oauth` open a REAL browser flow and hang the suite. Tests that need
    the fallback set GOOGLE_DOCS_MCP_LOCAL_CONFIG_PATH themselves afterwards.
    """
    monkeypatch.setenv("GOOGLE_DOCS_MCP_LOCAL_CONFIG_PATH", str(tmp_path / "none.json"))


@pytest.fixture
def configured_env(monkeypatch, tmp_path):
    """Fake OAuth client id/secret so is_configured is True in isolation.

    `settings` properties read os.environ live (see config.py), so setenv
    here is immediately visible to every module holding a `settings` reference
    — no singleton-recreation dance required.
    """
    monkeypatch.setenv("GOOGLE_DOCS_MCP_CLIENT_ID", "test-client-id.apps.googleusercontent.com")
    monkeypatch.setenv("GOOGLE_DOCS_MCP_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("GOOGLE_DOCS_MCP_TOKEN_PATH", str(tmp_path / "token.json"))
    from google_docs_mcp.config import settings

    yield settings


@pytest.fixture
def mock_docs_service(monkeypatch):
    service = MagicMock(name="docs_service")
    monkeypatch.setattr("google_docs_mcp.tools.docs_tool.get_docs_service", lambda: service)
    return service


@pytest.fixture
def mock_drive_service(monkeypatch):
    service = MagicMock(name="drive_service")
    monkeypatch.setattr("google_docs_mcp.tools.drive_tool.get_drive_service", lambda: service)
    return service
