"""google_drive — the Drive API v3 portmanteau tool (file lifecycle around Docs).

[RATIONALE] Docs API v1 only edits document *content*. Everything about a
document as a *file* — listing, searching, folders, sharing, permissions,
trash/delete, revisions, and comments — lives in Drive API v3. Splitting
these into a second portmanteau (rather than cramming them into `google_docs`)
keeps each tool's operation enum readable and matches the underlying API
boundary, per TOOL_DESIGN_STANDARDS.md §1.
"""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Any, Literal

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload
from pydantic import Field

from google_docs_mcp.google_client import get_drive_service, http_error_to_dict
from google_docs_mcp.oauth import NotAuthenticatedError, NotConfiguredError

DriveOperation = Literal[
    "list_files",
    "search",
    "get_metadata",
    "create_folder",
    "copy",
    "move",
    "rename",
    "trash",
    "untrash",
    "delete_permanently",
    "share",
    "list_permissions",
    "revoke_permission",
    "list_revisions",
    "list_comments",
    "add_comment",
    "reply_comment",
    "resolve_comment",
    "export",
    "import_file",
    "browse",
    "backup_folder",
    "restore_file",
]

GOOGLE_DOC_MIME = "application/vnd.google-apps.document"
GOOGLE_FOLDER_MIME = "application/vnd.google-apps.folder"

_FILE_FIELDS = "id, name, mimeType, modifiedTime, createdTime, size, webViewLink, parents, trashed, owners"

ExportFormat = Literal["pdf", "docx", "odt", "txt", "html", "rtf", "epub"]

_EXPORT_MIME_MAP: dict[str, str] = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "odt": "application/vnd.oasis.opendocument.text",
    "txt": "text/plain",
    "html": "text/html",
    "rtf": "application/rtf",
    "epub": "application/epub+zip",
}

# Source formats Drive will auto-convert into a Google Doc on import. Markdown
# has no native Drive mimetype — it's imported as plain text, so its literal
# `#`/`*` syntax lands as-is in the new doc rather than being rendered.
_IMPORT_MIME_MAP: dict[str, str] = {
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".txt": "text/plain",
    ".md": "text/plain",
    ".html": "text/html",
    ".htm": "text/html",
    ".rtf": "application/rtf",
}


def _not_ready(exc: NotConfiguredError | NotAuthenticatedError) -> dict[str, Any]:
    is_configured_issue = isinstance(exc, NotConfiguredError)
    return {
        "success": False,
        "error": str(exc),
        "error_type": "not_configured" if is_configured_issue else "not_authenticated",
        "suggestions": (
            [
                "See docs/ONBOARDING.md to create a Google Cloud OAuth client and set "
                "GOOGLE_DOCS_MCP_CLIENT_ID / GOOGLE_DOCS_MCP_CLIENT_SECRET."
            ]
            if is_configured_issue
            else ["Call google_docs_auth(operation='start_oauth') first."]
        ),
    }


_UNSAFE_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*]')


def _safe_filename(name: str) -> str:
    """Sanitize a Doc title for use as a local filename (Windows-safe)."""
    return _UNSAFE_FILENAME_CHARS.sub("_", name).strip().rstrip(".") or "untitled"


def _build_breadcrumbs(service: Any, folder_id: str) -> list[dict[str, str]]:
    """Walk the parent chain from `folder_id` up to Drive root for UI breadcrumbs."""
    chain: list[dict[str, str]] = []
    current_id: str | None = folder_id
    seen: set[str] = set()
    while current_id and current_id not in seen:
        seen.add(current_id)
        try:
            meta = service.files().get(fileId=current_id, fields="id, name, parents").execute()
        except HttpError:
            break
        chain.append({"id": meta["id"], "name": meta["name"]})
        parents = meta.get("parents") or []
        current_id = parents[0] if parents else None
    chain.reverse()
    return chain


def _collect_docs_in_folder(service: Any, folder_id: str | None, recursive: bool) -> list[dict[str, Any]]:
    """List Google Docs directly inside `folder_id` (Drive root if None), optionally recursing."""
    parent = folder_id or "root"
    resp = (
        service.files()
        .list(
            q=f"'{parent}' in parents and trashed = false and mimeType = '{GOOGLE_DOC_MIME}'",
            pageSize=1000,
            fields="files(id, name, modifiedTime)",
        )
        .execute()
    )
    docs: list[dict[str, Any]] = list(resp.get("files", []))
    if recursive:
        folders_resp = (
            service.files()
            .list(
                q=f"'{parent}' in parents and trashed = false and mimeType = '{GOOGLE_FOLDER_MIME}'",
                pageSize=1000,
                fields="files(id, name)",
            )
            .execute()
        )
        for sub in folders_resp.get("files", []):
            docs.extend(_collect_docs_in_folder(service, sub["id"], recursive=True))
    return docs


async def google_drive(
    operation: Annotated[
        DriveOperation,
        Field(description="Which Drive API operation to run. See docstring Operations table."),
    ],
    file_id: Annotated[
        str | None,
        Field(
            description="Target file/document id. Required for every operation except "
            "list_files, search, create_folder."
        ),
    ] = None,
    query: Annotated[
        str | None,
        Field(
            description="Free-text search term (search) or raw Drive query string (list_files). "
            "Required for: search."
        ),
    ] = None,
    folder_id: Annotated[
        str | None, Field(description="Parent folder id to filter/create under. Optional.")
    ] = None,
    docs_only: Annotated[
        bool, Field(description="Restrict list_files/search to Google Docs only. Default True.")
    ] = True,
    limit: Annotated[
        int,
        Field(
            description="Max results per page (list_files, search, list_revisions, "
            "list_comments). Default 25, max 100."
        ),
    ] = 25,
    cursor: Annotated[
        str | None,
        Field(
            description="Opaque page token from a previous response's next_cursor. Pass it back "
            "to fetch the next page."
        ),
    ] = None,
    name: Annotated[
        str | None, Field(description="New/target name. Required for: create_folder, rename.")
    ] = None,
    new_parent_id: Annotated[
        str | None, Field(description="Destination folder id. Required for: move.")
    ] = None,
    email: Annotated[str | None, Field(description="Grantee email address. Required for: share.")] = None,
    role: Annotated[
        Literal["reader", "commenter", "writer", "owner"],
        Field(description="Permission role for share. Default 'reader'."),
    ] = "reader",
    send_notification: Annotated[bool, Field(description="Email the grantee on share. Default True.")] = True,
    permission_id: Annotated[str | None, Field(description="Required for: revoke_permission.")] = None,
    confirm: Annotated[
        bool,
        Field(
            description="Must be explicitly True for delete_permanently — this operation is "
            "irreversible and bypasses trash."
        ),
    ] = False,
    comment_id: Annotated[
        str | None, Field(description="Required for: reply_comment, resolve_comment.")
    ] = None,
    content: Annotated[
        str | None, Field(description="Comment/reply body text. Required for: add_comment, reply_comment.")
    ] = None,
    export_format: Annotated[
        ExportFormat,
        Field(description="Target format for export. Default 'pdf'."),
    ] = "pdf",
    output_path: Annotated[
        str | None,
        Field(description="Local filesystem path to write the exported file to. Required for: export."),
    ] = None,
    file_path: Annotated[
        str | None,
        Field(
            description="Local filesystem path to upload. Required for: import_file. Supported source "
            "extensions: .docx, .odt, .txt, .md (imported as plain text), .html, .htm, .rtf."
        ),
    ] = None,
    output_dir: Annotated[
        str | None,
        Field(description="Local directory to export into. Required for: backup_folder."),
    ] = None,
    recursive: Annotated[
        bool, Field(description="Recurse into subfolders. Optional for: backup_folder. Default False.")
    ] = False,
) -> dict[str, Any]:
    """[RATIONALE] Portmanteau over Drive API v3 `files`, `permissions`, `revisions`,
    and `comments` resources scoped to Google Docs file management.

    ## Operations
    - list_files(folder_id?, docs_only, limit, cursor) — paginated file listing
    - search(query, docs_only, limit, cursor) — full-text + metadata search
    - get_metadata(file_id) — name, mimeType, owners, timestamps, webViewLink
    - create_folder(name, folder_id?) — create a Drive folder
    - copy(file_id, name?, folder_id?) — duplicate a file
    - move(file_id, new_parent_id) — reparent a file
    - rename(file_id, name)
    - trash(file_id) — reversible soft delete
    - untrash(file_id)
    - delete_permanently(file_id, confirm=True) — **irreversible**, bypasses trash
    - share(file_id, email, role, send_notification) — grant a permission
    - list_permissions(file_id)
    - revoke_permission(file_id, permission_id)
    - list_revisions(file_id, limit, cursor)
    - list_comments(file_id, limit, cursor)
    - add_comment(file_id, content)
    - reply_comment(file_id, comment_id, content)
    - resolve_comment(file_id, comment_id) — marks the comment thread resolved
    - export(file_id, export_format, output_path) — download a Google Doc as pdf/docx/odt/txt/html/rtf/epub
    - import_file(file_path, name?, folder_id?) — upload a local .docx/.odt/.txt/.md/.html/.rtf file,
      converted into a new Google Doc
    - browse(folder_id?, limit, cursor) — list the folders and Google Docs directly inside a folder
      (None/omitted = Drive root), plus the breadcrumb chain from root down to that folder. Folders
      are returned unpaginated (bounded — 200 direct subfolders covers any realistic case); the docs
      list is paginated the same way as list_files/search (`limit`/`cursor` in, `has_more`/
      `next_cursor` out) since a folder can hold far more documents than that
    - backup_folder(folder_id?, output_dir, export_format, recursive) — export every Google Doc in
      a folder to local files, with a `manifest.json` mapping doc id -> local path -> revision, so
      the same folder can be restored later
    - restore_file(file_id, file_path) — overwrite an **existing** Google Doc's content from a local
      file (the inverse of `export` — push a locally-edited backup copy back to Drive, not create
      a new doc)

    ## Return Format
    On success: `{"success": true, "message": str, "data": {...}}`. Paginated operations
    (list_files, search, list_revisions, list_comments) return
    `{"items": [...], "has_more": bool, "next_cursor": str | null}` inside `data` — pass
    `next_cursor` back as `cursor` to continue. `browse`'s `data` carries the same `has_more`/
    `next_cursor` pair (for its `files` list only — `folders` is unpaginated, see above).
    On failure: `{"success": false, "error": str, "error_type": str, "suggestions": [str]}`.

    ## Examples
    ```python
    await google_drive(operation="search", query="quarterly report")
    await google_drive(operation="list_files", folder_id="0AbC...", limit=50)
    await google_drive(operation="share", file_id="1AbC...", email="teammate@example.com",
                        role="commenter")
    await google_drive(operation="delete_permanently", file_id="1AbC...", confirm=True)
    await google_drive(operation="export", file_id="1AbC...", export_format="pdf",
                        output_path="C:/Users/me/Downloads/report.pdf")
    await google_drive(operation="import_file", file_path="C:/Users/me/Downloads/notes.docx",
                        name="Imported Notes")
    ```

    Notes:
    - `delete_permanently` requires `confirm=True` and cannot be undone — prefer `trash` for
      anything recoverable.
    - `docs_only=True` (the default) filters to `mimeType='application/vnd.google-apps.document'`;
      set False to see all Drive file types in the folder.
    - `export` is a Drive API v3 `files.export` call with a **10 MB** output size limit — for
      larger documents, export in a smaller/simpler format (`txt`/`html`) or split the document.
    - `import_file` on a `.md` source imports the literal Markdown text (Drive has no native
      Markdown converter) — headings/lists won't render as Docs formatting unless you follow up
      with `google_docs` style operations.
    """
    try:
        service = get_drive_service()
    except (NotConfiguredError, NotAuthenticatedError) as exc:
        return _not_ready(exc)

    limit = max(1, min(limit, 100))

    try:
        if operation in {"list_files", "search"}:
            clauses = ["trashed = false"]
            if docs_only:
                clauses.append(f"mimeType = '{GOOGLE_DOC_MIME}'")
            if folder_id:
                clauses.append(f"'{folder_id}' in parents")
            if operation == "search":
                if not query:
                    return {
                        "success": False,
                        "error": "query is required for search",
                        "error_type": "validation",
                    }
                escaped = query.replace("'", "\\'")
                clauses.append(f"fullText contains '{escaped}'")
            elif query:
                clauses.append(query)

            resp = (
                service.files()
                .list(
                    q=" and ".join(clauses),
                    pageSize=limit,
                    pageToken=cursor,
                    fields=f"nextPageToken, files({_FILE_FIELDS})",
                )
                .execute()
            )
            items = resp.get("files", [])
            next_cursor = resp.get("nextPageToken")
            return {
                "success": True,
                "message": f"Found {len(items)} file(s).",
                "data": {"items": items, "has_more": bool(next_cursor), "next_cursor": next_cursor},
            }

        if operation == "get_metadata":
            if not file_id:
                return {"success": False, "error": "file_id is required", "error_type": "validation"}
            meta = service.files().get(fileId=file_id, fields=_FILE_FIELDS).execute()
            return {"success": True, "message": f"Fetched metadata for {file_id}.", "data": {"file": meta}}

        if operation == "create_folder":
            if not name:
                return {"success": False, "error": "name is required", "error_type": "validation"}
            body: dict[str, Any] = {"name": name, "mimeType": GOOGLE_FOLDER_MIME}
            if folder_id:
                body["parents"] = [folder_id]
            created = service.files().create(body=body, fields=_FILE_FIELDS).execute()
            return {"success": True, "message": f"Created folder '{name}'.", "data": {"file": created}}

        if operation == "import_file":
            if not file_path:
                return {"success": False, "error": "file_path is required", "error_type": "validation"}
            src = Path(file_path)
            if not src.is_file():
                return {
                    "success": False,
                    "error": f"file not found: {src}",
                    "error_type": "validation",
                }
            source_mime = _IMPORT_MIME_MAP.get(src.suffix.lower())
            if not source_mime:
                return {
                    "success": False,
                    "error": f"unsupported source extension '{src.suffix}'",
                    "error_type": "validation",
                    "suggestions": [f"Supported: {', '.join(sorted(_IMPORT_MIME_MAP))}"],
                }
            body = {"name": name or src.stem, "mimeType": GOOGLE_DOC_MIME}
            if folder_id:
                body["parents"] = [folder_id]
            media = MediaFileUpload(str(src), mimetype=source_mime, resumable=False)
            created = service.files().create(body=body, media_body=media, fields=_FILE_FIELDS).execute()
            return {
                "success": True,
                "message": f"Imported '{src.name}' as Google Doc '{body['name']}'.",
                "data": {"file": created},
            }

        if operation == "browse":
            parent = folder_id or "root"
            # Folders are bounded — a Drive folder having 200+ direct subfolders is not a
            # realistic case worth paginating. Docs are the actually-unbounded side (a folder
            # can easily hold thousands of files), so `limit`/`cursor` apply there.
            folders_resp = (
                service.files()
                .list(
                    q=f"'{parent}' in parents and trashed = false and mimeType = '{GOOGLE_FOLDER_MIME}'",
                    pageSize=200,
                    fields=f"files({_FILE_FIELDS})",
                    orderBy="name",
                )
                .execute()
            )
            docs_resp = (
                service.files()
                .list(
                    q=f"'{parent}' in parents and trashed = false and mimeType = '{GOOGLE_DOC_MIME}'",
                    pageSize=limit,
                    pageToken=cursor,
                    fields=f"nextPageToken, files({_FILE_FIELDS})",
                    orderBy="name",
                )
                .execute()
            )
            breadcrumbs = _build_breadcrumbs(service, folder_id) if folder_id else []
            current = (
                service.files().get(fileId=folder_id, fields="id, name").execute() if folder_id else None
            )
            folders = folders_resp.get("files", [])
            docs = docs_resp.get("files", [])
            next_cursor = docs_resp.get("nextPageToken")
            return {
                "success": True,
                "message": f"{len(folders)} folder(s), {len(docs)} doc(s).",
                "data": {
                    "folder": current,
                    "breadcrumbs": breadcrumbs,
                    "folders": folders,
                    "files": docs,
                    "has_more": next_cursor is not None,
                    "next_cursor": next_cursor,
                },
            }

        if operation == "backup_folder":
            if not output_dir:
                return {"success": False, "error": "output_dir is required", "error_type": "validation"}
            out = Path(output_dir)
            out.mkdir(parents=True, exist_ok=True)
            docs = _collect_docs_in_folder(service, folder_id, recursive)
            mime = _EXPORT_MIME_MAP[export_format]
            manifest: dict[str, Any] = {
                "folder_id": folder_id,
                "exported_at": datetime.now(UTC).isoformat(),
                "export_format": export_format,
                "files": [],
            }
            errors: list[dict[str, str]] = []
            for doc in docs:
                dest = out / f"{_safe_filename(doc['name'])}.{export_format}"
                try:
                    data = service.files().export(fileId=doc["id"], mimeType=mime).execute()
                except HttpError as exc:
                    errors.append({"doc_id": doc["id"], "name": doc["name"], "error": str(exc)})
                    continue
                dest.write_bytes(data)
                manifest["files"].append(
                    {
                        "doc_id": doc["id"],
                        "name": doc["name"],
                        "local_path": str(dest),
                        "modified_time": doc.get("modifiedTime"),
                    }
                )
            manifest_path = out / "manifest.json"
            manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
            backed_up = len(manifest["files"])
            return {
                "success": True,
                "message": f"Backed up {backed_up} doc(s) to {out}"
                + (f" ({len(errors)} failed)." if errors else "."),
                "data": {
                    "output_dir": str(out),
                    "manifest_path": str(manifest_path),
                    "count": backed_up,
                    "errors": errors,
                },
            }

        if not file_id:
            return {"success": False, "error": "file_id is required", "error_type": "validation"}

        if operation == "copy":
            body = {}
            if name:
                body["name"] = name
            if folder_id:
                body["parents"] = [folder_id]
            copied = service.files().copy(fileId=file_id, body=body, fields=_FILE_FIELDS).execute()
            return {"success": True, "message": "Copied file.", "data": {"file": copied}}

        if operation == "move":
            if not new_parent_id:
                return {"success": False, "error": "new_parent_id is required", "error_type": "validation"}
            current = service.files().get(fileId=file_id, fields="parents").execute()
            previous_parents = ",".join(current.get("parents", []))
            updated = (
                service.files()
                .update(
                    fileId=file_id,
                    addParents=new_parent_id,
                    removeParents=previous_parents,
                    fields=_FILE_FIELDS,
                )
                .execute()
            )
            return {"success": True, "message": "Moved file.", "data": {"file": updated}}

        if operation == "rename":
            if not name:
                return {"success": False, "error": "name is required", "error_type": "validation"}
            updated = (
                service.files().update(fileId=file_id, body={"name": name}, fields=_FILE_FIELDS).execute()
            )
            return {"success": True, "message": f"Renamed to '{name}'.", "data": {"file": updated}}

        if operation == "trash":
            updated = (
                service.files().update(fileId=file_id, body={"trashed": True}, fields=_FILE_FIELDS).execute()
            )
            return {"success": True, "message": "Moved to trash.", "data": {"file": updated}}

        if operation == "untrash":
            updated = (
                service.files().update(fileId=file_id, body={"trashed": False}, fields=_FILE_FIELDS).execute()
            )
            return {"success": True, "message": "Restored from trash.", "data": {"file": updated}}

        if operation == "delete_permanently":
            if not confirm:
                return {
                    "success": False,
                    "error": "delete_permanently requires confirm=True (irreversible, bypasses trash)",
                    "error_type": "validation",
                    "suggestions": ["Use operation='trash' for a reversible delete."],
                }
            service.files().delete(fileId=file_id).execute()
            return {
                "success": True,
                "message": f"Permanently deleted {file_id}.",
                "data": {"file_id": file_id},
            }

        if operation == "share":
            if not email:
                return {"success": False, "error": "email is required", "error_type": "validation"}
            perm = (
                service.permissions()
                .create(
                    fileId=file_id,
                    body={"type": "user", "role": role, "emailAddress": email},
                    sendNotificationEmail=send_notification,
                    fields="id, role, emailAddress",
                )
                .execute()
            )
            return {
                "success": True,
                "message": f"Shared with {email} as {role}.",
                "data": {"permission": perm},
            }

        if operation == "list_permissions":
            resp = (
                service.permissions()
                .list(fileId=file_id, fields="permissions(id, role, emailAddress, type)")
                .execute()
            )
            return {
                "success": True,
                "message": "Listed permissions.",
                "data": {"items": resp.get("permissions", [])},
            }

        if operation == "revoke_permission":
            if not permission_id:
                return {"success": False, "error": "permission_id is required", "error_type": "validation"}
            service.permissions().delete(fileId=file_id, permissionId=permission_id).execute()
            return {
                "success": True,
                "message": "Permission revoked.",
                "data": {"permission_id": permission_id},
            }

        if operation == "list_revisions":
            resp = service.revisions().list(fileId=file_id, pageSize=limit, pageToken=cursor).execute()
            items = resp.get("revisions", [])
            next_cursor = resp.get("nextPageToken")
            return {
                "success": True,
                "message": f"Found {len(items)} revision(s).",
                "data": {"items": items, "has_more": bool(next_cursor), "next_cursor": next_cursor},
            }

        if operation == "list_comments":
            resp = (
                service.comments()
                .list(
                    fileId=file_id,
                    pageSize=limit,
                    pageToken=cursor,
                    fields="nextPageToken, comments(id, content, author, resolved, createdTime, replies)",
                )
                .execute()
            )
            items = resp.get("comments", [])
            next_cursor = resp.get("nextPageToken")
            return {
                "success": True,
                "message": f"Found {len(items)} comment(s).",
                "data": {"items": items, "has_more": bool(next_cursor), "next_cursor": next_cursor},
            }

        if operation == "add_comment":
            if not content:
                return {"success": False, "error": "content is required", "error_type": "validation"}
            comment = (
                service.comments()
                .create(fileId=file_id, body={"content": content}, fields="id, content, createdTime")
                .execute()
            )
            return {"success": True, "message": "Comment added.", "data": {"comment": comment}}

        if operation == "reply_comment":
            if not comment_id or not content:
                return {
                    "success": False,
                    "error": "comment_id and content are required",
                    "error_type": "validation",
                }
            reply = (
                service.replies()
                .create(fileId=file_id, commentId=comment_id, body={"content": content}, fields="id, content")
                .execute()
            )
            return {"success": True, "message": "Reply posted.", "data": {"reply": reply}}

        if operation == "resolve_comment":
            if not comment_id:
                return {"success": False, "error": "comment_id is required", "error_type": "validation"}
            reply = (
                service.replies()
                .create(
                    fileId=file_id,
                    commentId=comment_id,
                    body={"action": "resolve", "content": "Resolved."},
                    fields="id, action",
                )
                .execute()
            )
            return {"success": True, "message": "Comment resolved.", "data": {"reply": reply}}

        if operation == "export":
            if not output_path:
                return {"success": False, "error": "output_path is required", "error_type": "validation"}
            mime = _EXPORT_MIME_MAP[export_format]
            data = service.files().export(fileId=file_id, mimeType=mime).execute()
            dest = Path(output_path)
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            return {
                "success": True,
                "message": f"Exported to {dest} ({len(data)} bytes, {export_format}).",
                "data": {"output_path": str(dest), "format": export_format, "size_bytes": len(data)},
            }

        if operation == "restore_file":
            if not file_path:
                return {"success": False, "error": "file_path is required", "error_type": "validation"}
            src = Path(file_path)
            if not src.is_file():
                return {"success": False, "error": f"file not found: {src}", "error_type": "validation"}
            source_mime = _IMPORT_MIME_MAP.get(src.suffix.lower())
            if not source_mime:
                return {
                    "success": False,
                    "error": f"unsupported source extension '{src.suffix}'",
                    "error_type": "validation",
                    "suggestions": [f"Supported: {', '.join(sorted(_IMPORT_MIME_MAP))}"],
                }
            media = MediaFileUpload(str(src), mimetype=source_mime, resumable=False)
            updated = service.files().update(fileId=file_id, media_body=media, fields=_FILE_FIELDS).execute()
            return {
                "success": True,
                "message": f"Restored '{src.name}' into existing document {file_id}.",
                "data": {"file": updated},
            }

        return {"success": False, "error": f"Unknown operation '{operation}'", "error_type": "validation"}

    except HttpError as exc:
        return http_error_to_dict(exc)
