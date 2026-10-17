"""Unit tests for the Stitcher (src/google_docs_mcp/stitch.py)."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock

from google_docs_mcp import stitch


def _src(i, text="body text here"):
    return {
        "id": f"id-{i}",
        "name": f"Note {i}",
        "modifiedTime": "2026-10-16T09:00:00.000Z",
        "text": text,
    }


def test_build_stitched_sections_and_links():
    out = stitch.build_stitched([_src(1), _src(2, "other body")])
    assert "Note 1" in out["markdown"] and "Note 2" in out["markdown"]
    assert "body text here" in out["markdown"]
    assert "https://docs.google.com/document/d/id-1/edit" in out["markdown"]
    assert len(out["used"]) == 2 and out["skipped"] == []
    assert out["title"].startswith("Stitched notes")


def test_build_stitched_dedupes_and_skips_empty():
    out = stitch.build_stitched([_src(1), _src(2), _src(3, ""), _src(4, "  ")])
    assert len(out["used"]) == 1  # id-2 duplicate content dropped
    assert {s["reason"] for s in out["skipped"]} == {"duplicate content", "empty export"}
    out2 = stitch.build_stitched([_src(1)], skip_duplicates=False)
    assert len(out2["used"]) == 1


def test_build_stitched_custom_title():
    out = stitch.build_stitched([_src(1)], title="My compendium")
    assert out["title"] == "My compendium"
    assert out["markdown"].startswith("# My compendium")


def test_stitch_validation_errors():
    assert stitch.stitch_docs(mode="ids")["error_type"] == "validation"
    assert stitch.stitch_docs(mode="search")["error_type"] == "validation"


def test_preview_validation_errors():
    from google_docs_mcp.stitch import google_docs_stitch

    async def _run():
        bad_ids = await google_docs_stitch(operation="preview", mode="ids")
        assert "ids is required" in bad_ids["error"]
        bad_q = await google_docs_stitch(operation="preview", mode="search")
        assert "query is required" in bad_q["error"]

    asyncio.run(_run())


def _mocked_services(monkeypatch, bodies: dict[str, str]):
    """Drive listing + exports + Docs create/append, all in-memory."""
    drive = MagicMock(name="drive")
    docs = MagicMock(name="docs")

    listing = MagicMock()
    listing.execute.return_value = {
        "files": [
            {
                "id": fid,
                "name": f"Doc {fid}",
                "mimeType": stitch.DOC_MIME,
                "modifiedTime": "2026-10-16T00:00:00Z",
            }
            for fid in bodies
        ]
    }
    drive.files.return_value.list.return_value = listing

    def _export_media(fileId, mimeType):
        m = MagicMock()
        m._file_id = fileId
        return m

    drive.files.return_value.export_media.side_effect = _export_media

    class _FakeDl:
        def __init__(self, fd, request):
            fd.write(bodies[request._file_id].encode())

        def next_chunk(self):
            return (None, True)

    import googleapiclient.http

    monkeypatch.setattr(googleapiclient.http, "MediaIoBaseDownload", _FakeDl)

    created = MagicMock()
    created.execute.return_value = {"documentId": "new-doc-1"}
    docs.documents.return_value.create.return_value = created
    getter = MagicMock()
    getter.execute.return_value = {"body": {"content": [{"endIndex": 2}]}}
    docs.documents.return_value.get.return_value = getter
    docs.documents.return_value.batchUpdate.return_value.execute.return_value = {}

    monkeypatch.setattr("google_docs_mcp.stitch.get_drive_service", lambda: drive)
    monkeypatch.setattr("google_docs_mcp.stitch.get_docs_service", lambda: docs)
    return drive, docs


def test_stitch_creates_doc_with_mocked_services(monkeypatch):
    _mocked_services(monkeypatch, {"a": "alpha body here", "b": "beta body here"})

    async def _run():
        from google_docs_mcp.stitch import google_docs_stitch

        return await google_docs_stitch(operation="stitch", mode="recent", count=2, title="T")

    res = asyncio.run(_run())
    assert res["success"] is True, res
    assert res["data"]["document_id"] == "new-doc-1"
    assert res["data"]["url"].endswith("/edit")
    assert len(res["data"]["used"]) == 2


def test_preview_lists_candidates_with_mocked_services(monkeypatch):
    _mocked_services(monkeypatch, {"a": "x", "b": "y"})

    async def _run():
        from google_docs_mcp.stitch import google_docs_stitch

        return await google_docs_stitch(operation="preview", mode="recent", count=2)

    res = asyncio.run(_run())
    assert res["success"] is True
    assert [s["id"] for s in res["data"]["sources"]] == ["a", "b"]
