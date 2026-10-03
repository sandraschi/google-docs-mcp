"""Polling-based two-way sync between a local folder and a Google Drive folder.

[RATIONALE] A *true* live sync (like Google Drive Desktop or OneDrive) needs
either a publicly reachable HTTPS endpoint for Google's push notifications
(`files.watch`) or continuous local file-system watching tied to instant
push — neither is realistic for a local desktop app with no public endpoint.
This is a **polling** sync: on each pass, compare Drive's `modifiedTime` and
a local content hash against what was recorded at the last successful sync,
and reconcile. Honest tradeoff: not instant, but genuinely two-way and
unattended between passes.

Safety defaults — the reason data loss risk stays low even though this is a
sync engine touching real user files:
- A file changed on **both** sides since the last sync is a **conflict**,
  never silently overwritten: the local edit is renamed and kept, the doc's
  canonical content becomes whatever's on Drive.
- A doc that disappears from Drive (trashed) does **not** delete the local
  copy — it's moved into a `_remote_deleted/` subfolder instead.
- A file that disappears locally (accidental delete, moved out) does **not**
  trash the remote doc — the remote copy is authoritative and self-heals by
  being re-pulled on the next pass. (Asymmetric on purpose: an accidental
  local `rm` should never cascade into deleting the user's Drive document —
  and "come back next sync" is a safer failure mode than "silently stop
  syncing this one file with no visible signal why.")
"""

from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

from google_docs_mcp.tools.drive_tool import (
    _EXPORT_MIME_MAP,
    _IMPORT_MIME_MAP,
    GOOGLE_DOC_MIME,
    _safe_filename,
)

logger = logging.getLogger("google_docs_mcp.sync")

CONFLICT_SUFFIX_FMT = "%Y%m%d-%H%M%S"
DELETED_SUBDIR = "_remote_deleted"
MIN_INTERVAL_SECONDS = 60


@dataclass
class SyncConfig:
    enabled: bool = False
    local_dir: str | None = None
    folder_id: str | None = None
    interval_seconds: int = 300
    export_format: str = "docx"


def load_config(config_path: Path) -> SyncConfig:
    if not config_path.is_file():
        return SyncConfig()
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("Sync config at %s is corrupt — using defaults.", config_path)
        return SyncConfig()
    known_fields = {f for f in SyncConfig.__dataclass_fields__}
    return SyncConfig(**{k: v for k, v in data.items() if k in known_fields})


def save_config(config_path: Path, config: SyncConfig) -> None:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps(asdict(config), indent=2), encoding="utf-8")


@dataclass
class SyncManifestEntry:
    doc_id: str
    name: str
    local_path: str
    remote_modified_time: str | None
    local_hash: str | None


@dataclass
class SyncResult:
    pulled: list[str] = field(default_factory=list)
    pushed: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)
    remote_deleted: list[str] = field(default_factory=list)
    untracked_missing_local: list[str] = field(default_factory=list)
    errors: list[dict[str, str]] = field(default_factory=list)
    ran_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_manifest(manifest_path: Path) -> dict[str, SyncManifestEntry]:
    if not manifest_path.is_file():
        return {}
    try:
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        logger.warning("Sync manifest at %s is corrupt — starting fresh.", manifest_path)
        return {}
    return {doc_id: SyncManifestEntry(**entry) for doc_id, entry in raw.get("entries", {}).items()}


def save_manifest(manifest_path: Path, entries: dict[str, SyncManifestEntry]) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"entries": {doc_id: asdict(e) for doc_id, e in entries.items()}}
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _list_remote_docs(service: Any, folder_id: str | None) -> dict[str, dict[str, Any]]:
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
    return {f["id"]: f for f in resp.get("files", [])}


async def run_sync_pass(
    service: Any,
    *,
    local_dir: Path,
    folder_id: str | None,
    manifest_path: Path,
    export_format: str = "docx",
) -> SyncResult:
    """Run exactly one reconcile pass. Safe to call repeatedly (idempotent when
    nothing changed) — this is what both `run_once` and the background poll
    loop call."""
    result = SyncResult()
    local_dir.mkdir(parents=True, exist_ok=True)
    manifest = load_manifest(manifest_path)
    export_mime = _EXPORT_MIME_MAP[export_format]

    remote_docs = _list_remote_docs(service, folder_id)
    claimed_paths: set[str] = {e.local_path for e in manifest.values()}

    # 1. Reconcile every doc already being tracked.
    for doc_id, entry in list(manifest.items()):
        local_path = Path(entry.local_path)
        remote = remote_docs.get(doc_id)

        if remote is None:
            # Trashed/removed on Drive — never hard-delete the local copy.
            if local_path.is_file():
                deleted_dir = local_dir / DELETED_SUBDIR
                deleted_dir.mkdir(exist_ok=True)
                dest = deleted_dir / local_path.name
                local_path.replace(dest)
                result.remote_deleted.append(entry.name)
            del manifest[doc_id]
            continue

        local_exists = local_path.is_file()
        local_hash = _hash_file(local_path) if local_exists else None
        changed_local = local_exists and local_hash != entry.local_hash
        changed_remote = remote.get("modifiedTime") != entry.remote_modified_time

        if not local_exists:
            # Tracked file vanished locally (accidental delete, moved out, etc).
            # Self-heals by re-pulling — the remote copy is authoritative and is
            # never touched because of a local disappearance. Must re-pull (not
            # just drop from the manifest) in the SAME pass: dropping it would
            # make the "new remote docs" step below treat it as never-before-seen
            # and pull it right back anyway, just without a clean result label.
            data = service.files().export(fileId=doc_id, mimeType=export_mime).execute()
            local_path.write_bytes(data)
            manifest[doc_id] = SyncManifestEntry(
                doc_id, remote["name"], str(local_path), remote.get("modifiedTime"), _hash_file(local_path)
            )
            result.untracked_missing_local.append(entry.name)
            continue

        try:
            if changed_local and changed_remote:
                conflict_name = (
                    f"{local_path.stem} (conflict "
                    f"{datetime.now(UTC).strftime(CONFLICT_SUFFIX_FMT)}){local_path.suffix}"
                )
                local_path.replace(local_dir / conflict_name)
                data = service.files().export(fileId=doc_id, mimeType=export_mime).execute()
                local_path.write_bytes(data)
                manifest[doc_id] = SyncManifestEntry(
                    doc_id,
                    remote["name"],
                    str(local_path),
                    remote.get("modifiedTime"),
                    _hash_file(local_path),
                )
                result.conflicts.append(entry.name)
            elif changed_remote:
                data = service.files().export(fileId=doc_id, mimeType=export_mime).execute()
                local_path.write_bytes(data)
                manifest[doc_id] = SyncManifestEntry(
                    doc_id,
                    remote["name"],
                    str(local_path),
                    remote.get("modifiedTime"),
                    _hash_file(local_path),
                )
                result.pulled.append(entry.name)
            elif changed_local:
                source_mime = _IMPORT_MIME_MAP.get(local_path.suffix.lower())
                if not source_mime:
                    result.errors.append(
                        {"name": entry.name, "error": f"unsupported extension {local_path.suffix}"}
                    )
                    continue
                media = MediaFileUpload(str(local_path), mimetype=source_mime, resumable=False)
                updated = (
                    service.files()
                    .update(fileId=doc_id, media_body=media, fields="id, name, modifiedTime")
                    .execute()
                )
                manifest[doc_id] = SyncManifestEntry(
                    doc_id, updated["name"], str(local_path), updated.get("modifiedTime"), local_hash
                )
                result.pushed.append(entry.name)
            # else: neither changed — no-op, manifest entry stays as-is.
        except HttpError as exc:
            result.errors.append({"name": entry.name, "error": str(exc)})

    # 2. New remote docs not yet tracked — pull them.
    tracked_ids = set(manifest.keys())
    for doc_id, remote in remote_docs.items():
        if doc_id in tracked_ids:
            continue
        dest = local_dir / f"{_safe_filename(remote['name'])}.{export_format}"
        if str(dest) in claimed_paths:
            dest = local_dir / f"{_safe_filename(remote['name'])}-{doc_id[:6]}.{export_format}"
        try:
            data = service.files().export(fileId=doc_id, mimeType=export_mime).execute()
        except HttpError as exc:
            result.errors.append({"name": remote["name"], "error": str(exc)})
            continue
        dest.write_bytes(data)
        manifest[doc_id] = SyncManifestEntry(
            doc_id, remote["name"], str(dest), remote.get("modifiedTime"), _hash_file(dest)
        )
        claimed_paths.add(str(dest))
        result.pulled.append(remote["name"])

    # 3. New local files not yet tracked — push them as new docs.
    if local_dir.is_dir():
        for path in sorted(local_dir.iterdir()):
            if not path.is_file() or str(path) in claimed_paths or path.name == "manifest.json":
                continue
            source_mime = _IMPORT_MIME_MAP.get(path.suffix.lower())
            if not source_mime:
                continue
            body: dict[str, Any] = {"name": path.stem, "mimeType": GOOGLE_DOC_MIME}
            if folder_id:
                body["parents"] = [folder_id]
            try:
                media = MediaFileUpload(str(path), mimetype=source_mime, resumable=False)
                created = (
                    service.files()
                    .create(body=body, media_body=media, fields="id, name, modifiedTime")
                    .execute()
                )
            except HttpError as exc:
                result.errors.append({"name": path.name, "error": str(exc)})
                continue
            manifest[created["id"]] = SyncManifestEntry(
                created["id"], created["name"], str(path), created.get("modifiedTime"), _hash_file(path)
            )
            claimed_paths.add(str(path))
            result.pushed.append(path.name)

    save_manifest(manifest_path, manifest)
    return result
