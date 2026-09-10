"""Unit tests for google_drive — all Google API calls are mocked (see conftest.py)."""

from __future__ import annotations

import json

import pytest

from google_docs_mcp.tools.drive_tool import google_drive


async def test_list_files_paginates(configured_env, mock_drive_service):
    mock_drive_service.files().list().execute.return_value = {
        "files": [{"id": "1", "name": "Doc A"}],
        "nextPageToken": "abc",
    }
    result = await google_drive(operation="list_files", limit=10)
    assert result["success"] is True
    assert result["data"]["has_more"] is True
    assert result["data"]["next_cursor"] == "abc"
    assert result["data"]["items"][0]["id"] == "1"


async def test_search_requires_query(configured_env, mock_drive_service):
    result = await google_drive(operation="search", query=None)
    assert result["success"] is False
    assert result["error_type"] == "validation"


async def test_delete_permanently_requires_confirm(configured_env, mock_drive_service):
    result = await google_drive(operation="delete_permanently", file_id="1", confirm=False)
    assert result["success"] is False
    assert "confirm" in result["error"]


async def test_delete_permanently_with_confirm_calls_api(configured_env, mock_drive_service):
    result = await google_drive(operation="delete_permanently", file_id="1", confirm=True)
    assert result["success"] is True
    mock_drive_service.files().delete.assert_any_call(fileId="1")


async def test_share_grants_permission(configured_env, mock_drive_service):
    mock_drive_service.permissions().create().execute.return_value = {
        "id": "perm1",
        "role": "reader",
        "emailAddress": "someone@example.com",
    }
    result = await google_drive(operation="share", file_id="1", email="someone@example.com", role="reader")
    assert result["success"] is True
    assert result["data"]["permission"]["role"] == "reader"


async def test_move_reparents_using_current_parents(configured_env, mock_drive_service):
    mock_drive_service.files().get().execute.return_value = {"parents": ["old-parent"]}
    mock_drive_service.files().update().execute.return_value = {"id": "1", "name": "Doc"}
    result = await google_drive(operation="move", file_id="1", new_parent_id="new-parent")
    assert result["success"] is True


async def test_file_id_required_for_most_operations(configured_env, mock_drive_service):
    result = await google_drive(operation="trash", file_id=None)
    assert result["success"] is False
    assert result["error_type"] == "validation"


@pytest.mark.parametrize("limit,expected", [(0, 1), (500, 100), (25, 25)])
async def test_limit_is_clamped(configured_env, mock_drive_service, limit, expected):
    mock_drive_service.files().list().execute.return_value = {"files": []}
    await google_drive(operation="list_files", limit=limit)
    _, kwargs = mock_drive_service.files().list.call_args
    assert kwargs["pageSize"] == expected


async def test_export_requires_output_path(configured_env, mock_drive_service):
    result = await google_drive(operation="export", file_id="1", output_path=None)
    assert result["success"] is False
    assert result["error_type"] == "validation"


async def test_export_writes_file(configured_env, mock_drive_service, tmp_path):
    mock_drive_service.files().export().execute.return_value = b"%PDF-1.4 fake pdf bytes"
    dest = tmp_path / "out" / "report.pdf"
    result = await google_drive(operation="export", file_id="1", export_format="pdf", output_path=str(dest))
    assert result["success"] is True
    assert dest.exists()
    assert dest.read_bytes() == b"%PDF-1.4 fake pdf bytes"
    assert result["data"]["size_bytes"] == len(b"%PDF-1.4 fake pdf bytes")


async def test_import_file_requires_existing_file(configured_env, mock_drive_service, tmp_path):
    missing = tmp_path / "missing.docx"
    result = await google_drive(operation="import_file", file_path=str(missing))
    assert result["success"] is False
    assert result["error_type"] == "validation"


async def test_import_file_rejects_unsupported_extension(configured_env, mock_drive_service, tmp_path):
    src = tmp_path / "notes.exe"
    src.write_bytes(b"not a real doc")
    result = await google_drive(operation="import_file", file_path=str(src))
    assert result["success"] is False
    assert "unsupported source extension" in result["error"]


async def test_import_file_uploads_and_converts(configured_env, mock_drive_service, tmp_path):
    src = tmp_path / "notes.txt"
    src.write_text("hello world")
    mock_drive_service.files().create().execute.return_value = {
        "id": "newdoc123",
        "name": "notes",
        "mimeType": "application/vnd.google-apps.document",
    }
    result = await google_drive(operation="import_file", file_path=str(src))
    assert result["success"] is True
    assert result["data"]["file"]["id"] == "newdoc123"
    _, kwargs = mock_drive_service.files().create.call_args
    assert kwargs["body"]["mimeType"] == "application/vnd.google-apps.document"
    assert kwargs["body"]["name"] == "notes"


async def test_import_file_uses_explicit_name(configured_env, mock_drive_service, tmp_path):
    src = tmp_path / "notes.txt"
    src.write_text("hello world")
    mock_drive_service.files().create().execute.return_value = {"id": "x", "name": "Custom Name"}
    await google_drive(operation="import_file", file_path=str(src), name="Custom Name")
    _, kwargs = mock_drive_service.files().create.call_args
    assert kwargs["body"]["name"] == "Custom Name"


async def test_browse_root_lists_folders_and_docs(configured_env, mock_drive_service):
    mock_drive_service.files().list().execute.side_effect = [
        {"files": [{"id": "f1", "name": "Reports"}]},  # folders query
        {"files": [{"id": "d1", "name": "Q3 Report"}]},  # docs query
    ]
    result = await google_drive(operation="browse")
    assert result["success"] is True
    assert result["data"]["folder"] is None
    assert result["data"]["breadcrumbs"] == []
    assert result["data"]["folders"][0]["name"] == "Reports"
    assert result["data"]["files"][0]["name"] == "Q3 Report"


async def test_browse_subfolder_includes_breadcrumbs(configured_env, mock_drive_service):
    mock_drive_service.files().list().execute.side_effect = [
        {"files": []},  # folders query
        {"files": [{"id": "d1", "name": "Doc in subfolder"}]},  # docs query
    ]
    mock_drive_service.files().get().execute.side_effect = [
        {"id": "sub1", "name": "Sub", "parents": []},  # breadcrumb walk
        {"id": "sub1", "name": "Sub"},  # current folder metadata
    ]
    result = await google_drive(operation="browse", folder_id="sub1")
    assert result["success"] is True
    assert result["data"]["folder"]["name"] == "Sub"
    assert result["data"]["breadcrumbs"] == [{"id": "sub1", "name": "Sub"}]


async def test_browse_paginates_docs_but_not_folders(configured_env, mock_drive_service):
    mock_drive_service.files().list().execute.side_effect = [
        {"files": [{"id": "f1", "name": "Reports"}]},  # folders query — no pageToken in response
        {
            "files": [{"id": "d1", "name": "Doc 1"}],
            "nextPageToken": "page2",
        },  # docs query — more pages available
    ]
    result = await google_drive(operation="browse", limit=1)
    assert result["success"] is True
    assert result["data"]["has_more"] is True
    assert result["data"]["next_cursor"] == "page2"
    # folders list has no pagination fields — it's returned in full every call
    assert "has_more" not in result["data"]["folders"]


async def test_browse_no_more_docs_reports_has_more_false(configured_env, mock_drive_service):
    mock_drive_service.files().list().execute.side_effect = [
        {"files": []},
        {"files": [{"id": "d1", "name": "Only Doc"}]},  # no nextPageToken
    ]
    result = await google_drive(operation="browse")
    assert result["data"]["has_more"] is False
    assert result["data"]["next_cursor"] is None


async def test_backup_folder_requires_output_dir(configured_env, mock_drive_service):
    result = await google_drive(operation="backup_folder", output_dir=None)
    assert result["success"] is False
    assert result["error_type"] == "validation"


async def test_backup_folder_writes_files_and_manifest(configured_env, mock_drive_service, tmp_path):
    mock_drive_service.files().list().execute.return_value = {
        "files": [{"id": "d1", "name": "My Doc", "modifiedTime": "2026-09-01T00:00:00Z"}]
    }
    mock_drive_service.files().export().execute.return_value = b"%PDF-1.4 fake"
    out_dir = tmp_path / "backup"

    result = await google_drive(operation="backup_folder", output_dir=str(out_dir), export_format="pdf")

    assert result["success"] is True
    assert result["data"]["count"] == 1
    doc_file = out_dir / "My Doc.pdf"
    assert doc_file.exists()
    assert doc_file.read_bytes() == b"%PDF-1.4 fake"
    manifest = json.loads((out_dir / "manifest.json").read_text())
    assert manifest["files"][0]["doc_id"] == "d1"
    assert manifest["files"][0]["local_path"] == str(doc_file)


async def test_backup_folder_sanitizes_unsafe_filenames(configured_env, mock_drive_service, tmp_path):
    mock_drive_service.files().list().execute.return_value = {
        "files": [{"id": "d1", "name": "Report: Q3 / Final?", "modifiedTime": None}]
    }
    mock_drive_service.files().export().execute.return_value = b"data"
    out_dir = tmp_path / "backup"

    result = await google_drive(operation="backup_folder", output_dir=str(out_dir))

    assert result["success"] is True
    written = list(out_dir.glob("*.pdf"))
    assert len(written) == 1
    assert "/" not in written[0].name
    assert ":" not in written[0].name


async def test_restore_file_requires_existing_local_file(configured_env, mock_drive_service, tmp_path):
    missing = tmp_path / "missing.docx"
    result = await google_drive(operation="restore_file", file_id="d1", file_path=str(missing))
    assert result["success"] is False
    assert result["error_type"] == "validation"


async def test_restore_file_updates_existing_doc(configured_env, mock_drive_service, tmp_path):
    src = tmp_path / "edited.txt"
    src.write_text("updated content")
    mock_drive_service.files().update().execute.return_value = {"id": "d1", "name": "My Doc"}

    result = await google_drive(operation="restore_file", file_id="d1", file_path=str(src))

    assert result["success"] is True
    assert result["data"]["file"]["id"] == "d1"
    _, kwargs = mock_drive_service.files().update.call_args
    assert kwargs["fileId"] == "d1"
