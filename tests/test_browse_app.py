"""Unit tests for show_google_drive_folder_app (Prefab card wrapping google_drive browse)."""

from __future__ import annotations

from google_docs_mcp.tools.browse_app import show_google_drive_folder_app


async def test_browse_app_reports_not_configured():
    result = await show_google_drive_folder_app()
    assert "not set" in result.content[0].text or "onboard" in result.content[0].text.lower()


async def test_browse_app_renders_folder_contents(configured_env, mock_drive_service):
    mock_drive_service.files().list().execute.side_effect = [
        {"files": [{"id": "f1", "name": "Reports"}]},
        {"files": [{"id": "d1", "name": "Q3 Report", "modifiedTime": "2026-09-01T00:00:00Z"}]},
    ]
    result = await show_google_drive_folder_app()
    assert "1 folder" in result.content[0].text
    assert "1 doc" in result.content[0].text
    assert result.structured_content is not None


async def test_browse_app_handles_empty_folder(configured_env, mock_drive_service):
    mock_drive_service.files().list().execute.side_effect = [
        {"files": []},
        {"files": []},
    ]
    result = await show_google_drive_folder_app()
    assert "0 folder" in result.content[0].text
    assert "0 doc" in result.content[0].text
