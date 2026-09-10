"""Unit tests for google_docs_convert_advanced (the libreoffice-mcp bridge)."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

from google_docs_mcp.tools import libreoffice_tool
from google_docs_mcp.tools.libreoffice_tool import google_docs_convert_advanced


async def test_export_failure_short_circuits_before_libreoffice_call(monkeypatch):
    async def fake_export(**kwargs):
        return {"success": False, "error": "not configured", "error_type": "not_configured"}

    monkeypatch.setattr(libreoffice_tool, "google_drive", fake_export)
    called = AsyncMock()
    monkeypatch.setattr(libreoffice_tool, "convert_via_libreoffice", called)

    result = await google_docs_convert_advanced(file_id="x", output_format="doc", output_path="C:/out.doc")

    assert result["success"] is False
    assert result["error_type"] == "not_configured"
    called.assert_not_called()


async def test_libreoffice_unavailable_after_successful_export(monkeypatch, tmp_path):
    exported = tmp_path / "source.docx"

    async def fake_export(*, output_path, **kwargs):
        exported.write_bytes(b"fake docx")
        return {"success": True, "message": "exported", "data": {"output_path": output_path}}

    async def fake_convert(*args, **kwargs):
        raise libreoffice_tool.LibreOfficeUnavailableError("libreoffice-mcp not reachable at http://x")

    monkeypatch.setattr(libreoffice_tool, "google_drive", fake_export)
    monkeypatch.setattr(libreoffice_tool, "convert_via_libreoffice", fake_convert)

    result = await google_docs_convert_advanced(
        file_id="x", output_format="doc", output_path=str(tmp_path / "out.doc")
    )

    assert result["success"] is False
    assert result["error_type"] == "dependency_unavailable"
    assert "not reachable" in result["error"]


async def test_successful_conversion_copies_output(monkeypatch, tmp_path):
    async def fake_export(*, output_path, **kwargs):
        Path(output_path).write_bytes(b"fake docx")
        return {"success": True, "message": "exported", "data": {"output_path": output_path}}

    produced = tmp_path / "produced.doc"
    produced.write_bytes(b"converted bytes")

    async def fake_convert(input_path, output_format):
        return {
            "success": True,
            "message": "converted",
            "data": {"success": True, "output": str(produced), "error": None},
        }

    monkeypatch.setattr(libreoffice_tool, "google_drive", fake_export)
    monkeypatch.setattr(libreoffice_tool, "convert_via_libreoffice", fake_convert)

    dest = tmp_path / "final" / "out.doc"
    result = await google_docs_convert_advanced(file_id="x", output_format="doc", output_path=str(dest))

    assert result["success"] is True
    assert dest.exists()
    assert dest.read_bytes() == b"converted bytes"
    assert result["data"]["output_path"] == str(dest)


async def test_libreoffice_reports_conversion_failure(monkeypatch, tmp_path):
    async def fake_export(*, output_path, **kwargs):
        Path(output_path).write_bytes(b"fake docx")
        return {"success": True, "message": "exported", "data": {"output_path": output_path}}

    async def fake_convert(input_path, output_format):
        return {
            "success": True,
            "message": "",
            "data": {"success": False, "output": None, "error": "soffice failed: timeout"},
        }

    monkeypatch.setattr(libreoffice_tool, "google_drive", fake_export)
    monkeypatch.setattr(libreoffice_tool, "convert_via_libreoffice", fake_convert)

    result = await google_docs_convert_advanced(
        file_id="x", output_format="doc", output_path=str(tmp_path / "out.doc")
    )

    assert result["success"] is False
    assert result["error_type"] == "api_error"
    assert "timeout" in result["error"]
