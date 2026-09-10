"""Unit tests for google_docs_sync (the tool wrapper around sync_engine).

Every test isolates state via GOOGLE_DOCS_MCP_SYNC_CONFIG_PATH /
_SYNC_MANIFEST_PATH env vars pointed at tmp_path — never touches this repo's
real data/ directory (see sync_tool.sync_config_path()/sync_manifest_path()).
"""

from __future__ import annotations

import pytest

from google_docs_mcp.tools.sync_tool import google_docs_sync


@pytest.fixture(autouse=True)
def isolated_sync_paths(monkeypatch, tmp_path):
    monkeypatch.setenv("GOOGLE_DOCS_MCP_SYNC_CONFIG_PATH", str(tmp_path / "sync_config.json"))
    monkeypatch.setenv("GOOGLE_DOCS_MCP_SYNC_MANIFEST_PATH", str(tmp_path / "sync_manifest.json"))


async def test_configure_requires_local_dir():
    result = await google_docs_sync(operation="configure", local_dir=None)
    assert result["success"] is False
    assert result["error_type"] == "validation"


async def test_configure_then_status_reflects_it(tmp_path):
    await google_docs_sync(operation="configure", local_dir=str(tmp_path / "sync"), interval_seconds=120)
    result = await google_docs_sync(operation="status")
    assert result["success"] is True
    assert result["data"]["config"]["local_dir"] == str(tmp_path / "sync")
    assert result["data"]["config"]["enabled"] is False
    assert result["data"]["config"]["interval_seconds"] == 120
    assert result["data"]["tracked_count"] == 0


async def test_configure_clamps_interval_to_minimum(tmp_path):
    await google_docs_sync(operation="configure", local_dir=str(tmp_path / "sync"), interval_seconds=5)
    result = await google_docs_sync(operation="status")
    assert result["data"]["config"]["interval_seconds"] == 60


async def test_enable_without_configure_fails():
    result = await google_docs_sync(operation="enable")
    assert result["success"] is False
    assert result["error_type"] == "validation"


async def test_enable_then_disable_round_trip(tmp_path):
    await google_docs_sync(operation="configure", local_dir=str(tmp_path / "sync"))
    enabled = await google_docs_sync(operation="enable")
    assert enabled["data"]["enabled"] is True

    status = await google_docs_sync(operation="status")
    assert status["data"]["config"]["enabled"] is True

    disabled = await google_docs_sync(operation="disable")
    assert disabled["data"]["enabled"] is False


async def test_run_once_without_configure_fails():
    result = await google_docs_sync(operation="run_once")
    assert result["success"] is False
    assert result["error_type"] == "validation"


async def test_run_once_without_oauth_returns_not_configured(monkeypatch, tmp_path):
    monkeypatch.delenv("GOOGLE_DOCS_MCP_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_DOCS_MCP_CLIENT_SECRET", raising=False)
    await google_docs_sync(operation="configure", local_dir=str(tmp_path / "sync"))

    result = await google_docs_sync(operation="run_once")

    assert result["success"] is False
    assert result["error_type"] == "not_configured"


async def test_unknown_operation():
    result = await google_docs_sync(operation="bogus")  # type: ignore[arg-type]
    assert result["success"] is False
    assert result["error_type"] == "validation"
