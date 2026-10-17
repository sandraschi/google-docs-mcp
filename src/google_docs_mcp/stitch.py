"""Stitcher: combine small chat-export docs into one compendium Google Doc.

Standard flow: a bunch of iPad chat steps saved as small docs -> pick them
(recent N, search, or explicit ids) -> one button -> a new Google Doc with
titled sections, source links, and duplicate exports removed.

Pure builder (`build_stitched`) is fully unit-tested; the service half
(`stitch_docs`) talks to Drive/Docs and is covered with mocked services.
"""

from __future__ import annotations

import asyncio
import hashlib
import io
from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from pydantic import Field

from google_docs_mcp.google_client import get_docs_service, get_drive_service
from google_docs_mcp.oauth import NotAuthenticatedError, NotConfiguredError

DOC_MIME = "application/vnd.google-apps.document"
APPEND_CHUNK = 8000


def _not_ready(exc: Exception) -> dict[str, Any]:
    return {
        "success": False,
        "error": str(exc),
        "error_type": "not_authenticated",
        "suggestions": ["Call google_docs_auth(operation='start_oauth') first."],
    }


def build_stitched(
    sources: list[dict[str, Any]], title: str | None = None, skip_duplicates: bool = True
) -> dict[str, Any]:
    """Assemble stitched markdown from exported texts. Pure function.

    sources: [{id, name, modifiedTime?, text}]. Duplicate content (by hash)
    is kept once when skip_duplicates. Returns {title, markdown, used, skipped}.
    """
    seen: set[str] = set()
    used: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for src in sources:
        text = (src.get("text") or "").strip()
        if not text:
            skipped.append({"id": src.get("id"), "name": src.get("name"), "reason": "empty export"})
            continue
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
        if skip_duplicates and digest in seen:
            skipped.append({"id": src.get("id"), "name": src.get("name"), "reason": "duplicate content"})
            continue
        seen.add(digest)
        used.append({**src, "digest": digest})
    stamp = datetime.now(UTC).strftime("%Y-%m-%d")
    doc_title = title or f"Stitched notes {stamp} ({len(used)} sources)"
    parts = [f"# {doc_title}", ""]
    for src in used:
        link = f"https://docs.google.com/document/d/{src['id']}/edit"
        parts += [
            f"## {src.get('name', '(untitled)')}",
            f"- source: [{src.get('name', 'doc')}]({link}) | modified: {src.get('modifiedTime', '?')}",
            "",
            src["text"],
            "",
            "---",
            "",
        ]
    return {"title": doc_title, "markdown": "\n".join(parts), "used": used, "skipped": skipped}


def _export_text(drive: Any, file_id: str) -> str:
    from googleapiclient.http import MediaIoBaseDownload

    req = drive.files().export_media(fileId=file_id, mimeType="text/plain")
    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, req)
    done = False
    while not done:
        _, done = downloader.next_chunk()
    return buf.getvalue().decode("utf-8", errors="replace")


def stitch_docs(
    mode: str = "recent",
    count: int = 10,
    query: str | None = None,
    ids: list[str] | None = None,
    title: str | None = None,
    skip_duplicates: bool = True,
) -> dict[str, Any]:
    """List -> export -> build -> create -> append. Returns new doc link."""
    if (err := _check_mode_args(mode, query, ids)) is not None:
        return {"success": False, "error": err, "error_type": "validation"}
    try:
        drive = get_drive_service()
        docs = get_docs_service()
    except (NotConfiguredError, NotAuthenticatedError) as exc:
        return _not_ready(exc)
    try:
        if mode == "ids":
            assert ids is not None
            metas = []
            for fid in ids[:50]:
                meta = drive.files().get(fileId=fid, fields="id,name,mimeType,modifiedTime").execute()
                metas.append(meta)
        else:
            q = f"mimeType='{DOC_MIME}'"
            if mode == "search":
                assert query is not None
                q += f" and fullText contains '{query}'"
            metas = (
                drive.files()
                .list(
                    q=q,
                    pageSize=max(1, min(count or 10, 50)),
                    orderBy="modifiedTime desc",
                    fields="files(id,name,mimeType,modifiedTime)",
                )
                .execute()
                .get("files", [])
            )
        sources = []
        for meta in metas:
            if meta.get("mimeType") != DOC_MIME:
                continue
            try:
                text = _export_text(drive, meta["id"])
            except Exception as exc:
                text = ""
                sources.append({**meta, "text": text, "export_error": str(exc)[:160]})
                continue
            sources.append({**meta, "text": text})
        built = build_stitched(sources, title=title, skip_duplicates=skip_duplicates)
        if not built["used"]:
            return {
                "success": False,
                "error": "Nothing to stitch (all exports empty).",
                "error_type": "empty",
            }
        created = docs.documents().create(body={"title": built["title"]}).execute()
        doc_id = created["documentId"]
        body = built["markdown"]
        for i in range(0, len(body), APPEND_CHUNK):
            chunk = body[i : i + APPEND_CHUNK]
            if i == 0:
                # Fresh doc ends with a single empty paragraph: replace from index 1.
                reqs: list[dict[str, Any]] = [{"insertText": {"location": {"index": 1}, "text": chunk}}]
            else:
                doc = docs.documents().get(documentId=doc_id, fields="body(content(endIndex))").execute()
                end = max(x.get("endIndex", 2) - 1 for x in doc.get("body", {}).get("content", [{}]) if x)
                reqs = [{"insertText": {"location": {"index": end}, "text": chunk}}]
            docs.documents().batchUpdate(documentId=doc_id, body={"requests": reqs}).execute()
        return {
            "success": True,
            "message": f"Stitched {len(built['used'])} doc(s) into '{built['title']}'.",
            "data": {
                "document_id": doc_id,
                "url": f"https://docs.google.com/document/d/{doc_id}/edit",
                "title": built["title"],
                "used": [{"id": s["id"], "name": s.get("name")} for s in built["used"]],
                "skipped": built["skipped"],
            },
        }
    except Exception as exc:
        return {"success": False, "error": str(exc)[:300], "error_type": "api_error"}


async def google_docs_stitch(
    operation: Annotated[
        Literal["preview", "stitch"],
        Field(
            description="'preview' lists what would be stitched (no doc created). "
            "'stitch' builds the compendium as a NEW Google Doc and returns its link."
        ),
    ] = "preview",
    mode: Annotated[
        Literal["recent", "search", "ids"],
        Field(description="Source picker: recent N docs, full-text search, or explicit ids."),
    ] = "recent",
    count: Annotated[int, Field(description="How many recent docs (recent mode, 1-50).")] = 10,
    query: Annotated[str | None, Field(description="Search text (search mode).")] = None,
    ids: Annotated[list[str] | None, Field(description="Document ids (ids mode).")] = None,
    title: Annotated[str | None, Field(description="Compendium title (default: dated).")] = None,
    skip_duplicates: Annotated[bool, Field(description="Keep duplicate exports once.")] = True,
) -> dict[str, Any]:
    """Stitch small chat-export docs into one compendium Google Doc.

    The iPad flow: many small saved docs -> this tool -> one new doc with
    titled sections + source links. `preview` first (free), `stitch` when the
    source list looks right. Blocking network calls run off the event loop.
    """
    if operation == "preview":
        if (err := _check_mode_args(mode, query, ids)) is not None:
            return {"success": False, "error": err, "error_type": "validation"}
        try:
            drive = get_drive_service()
        except (NotConfiguredError, NotAuthenticatedError) as exc:
            return _not_ready(exc)
        try:
            result = await asyncio.to_thread(_preview_sources, drive, mode, count, query, ids)
            return {"success": True, "message": f"{len(result)} candidate(s).", "data": {"sources": result}}
        except Exception as exc:
            return {"success": False, "error": str(exc)[:300], "error_type": "api_error"}
    if operation == "stitch":
        return await asyncio.to_thread(stitch_docs, mode, count, query, ids, title, skip_duplicates)
    return {"success": False, "error": f"Unknown operation '{operation}'", "error_type": "validation"}


def _check_mode_args(mode: str, query: str | None, ids: list[str] | None) -> str | None:
    """Validation before any auth/network, so errors are actionable."""
    if mode == "ids" and not ids:
        return "ids is required for mode='ids'"
    if mode == "search" and not query:
        return "query is required for mode='search'"
    if mode not in ("recent", "search", "ids"):
        return f"Unknown mode '{mode}'. Valid: recent, search, ids."
    return None


def _preview_sources(
    drive: Any,
    mode: str,
    count: int,
    query: str | None,
    ids: list[str] | None,
) -> list[dict[str, Any]]:
    """Source metadata without exporting bodies (cheap pre-flight)."""
    if (err := _check_mode_args(mode, query, ids)) is not None:
        raise ValueError(err)
    if mode == "ids":
        assert ids is not None
        out = []
        for fid in ids[:50]:
            meta = drive.files().get(fileId=fid, fields="id,name,mimeType,modifiedTime").execute()
            out.append({k: meta.get(k) for k in ("id", "name", "mimeType", "modifiedTime")})
        return out
    q = f"mimeType='{DOC_MIME}'"
    if mode == "search":
        if not query:
            raise ValueError("query is required for mode='search'")
        q += f" and fullText contains '{query}'"
    res = (
        drive.files()
        .list(
            q=q,
            pageSize=max(1, min(count or 10, 50)),
            orderBy="modifiedTime desc",
            fields="files(id,name,mimeType,modifiedTime)",
        )
        .execute()
    )
    return [{k: m.get(k) for k in ("id", "name", "mimeType", "modifiedTime")} for m in res.get("files", [])]
