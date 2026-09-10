"""Unit tests for show_google_docs_sync_status_app (Prefab card wrapping google_docs_sync status)."""

from __future__ import annotations

import pytest

from google_docs_mcp.tools.sync_status_app import show_google_docs_sync_status_app
from google_docs_mcp.tools.sync_tool import google_docs_sync


@pytest.fixture(autouse=True)
def isolated_sync_paths(monkeypatch, tmp_path):
    monkeypatch.setenv("GOOGLE_DOCS_MCP_SYNC_CONFIG_PATH", str(tmp_path / "sync_config.json"))
    monkeypatch.setenv("GOOGLE_DOCS_MCP_SYNC_MANIFEST_PATH", str(tmp_path / "sync_manifest.json"))


async def test_sync_status_app_reports_not_configured():
    result = await show_google_docs_sync_status_app()
    assert result.content[0].text == "Sync not configured yet."


async def test_sync_status_app_reports_configured_and_enabled(tmp_path):
    await google_docs_sync(operation="configure", local_dir=str(tmp_path / "mirror"))
    await google_docs_sync(operation="enable")
    result = await show_google_docs_sync_status_app()
    assert "enabled" in result.content[0].text
    assert result.structured_content is not None


async def test_sync_status_app_reports_configured_and_disabled(tmp_path):
    await google_docs_sync(operation="configure", local_dir=str(tmp_path / "mirror"))
    result = await show_google_docs_sync_status_app()
    assert "disabled" in result.content[0].text
