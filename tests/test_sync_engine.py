"""Tests for the two-way sync reconcile logic — the highest-risk code in this
repo (it touches real local files and real Drive documents), so this suite
is intentionally more thorough than most.

Uses a hand-rolled fake Drive service rather than MagicMock: the reconcile
logic makes several distinct calls (list/export/update/create) whose
*interactions* with each other matter (e.g. "update, then does the next pass
see the new modifiedTime?"), which is much clearer to express as a small
stateful fake than as a MagicMock side_effect queue.
"""

from __future__ import annotations

import json

import pytest

import google_docs_mcp.sync_engine as sync_engine
from google_docs_mcp.sync_engine import (
    SyncConfig,
    load_config,
    load_manifest,
    run_sync_pass,
    save_config,
)


class _FakeMediaUpload:
    """Stand-in for googleapiclient.http.MediaFileUpload — records the path
    instead of doing real multipart encoding."""

    def __init__(self, path, mimetype=None, resumable=False):
        self.path = path


class _FakeExecutable:
    def __init__(self, value):
        self._value = value

    def execute(self):
        return self._value


class _FakeFiles:
    def __init__(self, service: FakeDriveService):
        self.service = service

    def list(self, q, pageSize, fields):
        items = [
            {"id": doc_id, "name": d["name"], "modifiedTime": d["modifiedTime"]}
            for doc_id, d in self.service.docs.items()
            if not d.get("trashed")
        ]
        return _FakeExecutable({"files": items})

    def export(self, fileId, mimeType):
        return _FakeExecutable(self.service.docs[fileId]["content"])

    def update(self, fileId, media_body, fields):
        from pathlib import Path

        content = Path(media_body.path).read_bytes()
        self.service.clock += 1
        new_time = f"t{self.service.clock}"
        self.service.docs[fileId]["content"] = content
        self.service.docs[fileId]["modifiedTime"] = new_time
        return _FakeExecutable(
            {"id": fileId, "name": self.service.docs[fileId]["name"], "modifiedTime": new_time}
        )

    def create(self, body, media_body, fields):
        from pathlib import Path

        self.service.clock += 1
        doc_id = f"new{self.service.clock}"
        content = Path(media_body.path).read_bytes()
        self.service.docs[doc_id] = {
            "name": body["name"],
            "modifiedTime": f"t{self.service.clock}",
            "content": content,
        }
        return _FakeExecutable(
            {"id": doc_id, "name": body["name"], "modifiedTime": self.service.docs[doc_id]["modifiedTime"]}
        )


class FakeDriveService:
    def __init__(self):
        self.docs: dict[str, dict] = {}
        self.clock = 0

    def add_doc(self, name: str, content: bytes = b"remote content") -> str:
        self.clock += 1
        doc_id = f"doc{self.clock}"
        self.docs[doc_id] = {"name": name, "modifiedTime": f"t{self.clock}", "content": content}
        return doc_id

    def files(self):
        return _FakeFiles(self)


@pytest.fixture(autouse=True)
def patch_media_upload(monkeypatch):
    monkeypatch.setattr(sync_engine, "MediaFileUpload", _FakeMediaUpload)


@pytest.fixture
def service():
    return FakeDriveService()


async def test_fresh_sync_pulls_all_remote_docs(service, tmp_path):
    service.add_doc("Doc A", b"content A")
    service.add_doc("Doc B", b"content B")
    local_dir = tmp_path / "sync"
    manifest_path = tmp_path / "manifest.json"

    result = await run_sync_pass(
        service, local_dir=local_dir, folder_id=None, manifest_path=manifest_path, export_format="docx"
    )

    assert set(result.pulled) == {"Doc A", "Doc B"}
    assert (local_dir / "Doc A.docx").read_bytes() == b"content A"
    assert (local_dir / "Doc B.docx").read_bytes() == b"content B"
    manifest = load_manifest(manifest_path)
    assert len(manifest) == 2


async def test_second_pass_with_no_changes_is_a_noop(service, tmp_path):
    service.add_doc("Doc A", b"content A")
    local_dir = tmp_path / "sync"
    manifest_path = tmp_path / "manifest.json"

    await run_sync_pass(service, local_dir=local_dir, folder_id=None, manifest_path=manifest_path)
    result = await run_sync_pass(service, local_dir=local_dir, folder_id=None, manifest_path=manifest_path)

    assert result.pulled == []
    assert result.pushed == []
    assert result.conflicts == []
    assert result.errors == []


async def test_remote_only_change_pulls(service, tmp_path):
    doc_id = service.add_doc("Doc A", b"v1")
    local_dir = tmp_path / "sync"
    manifest_path = tmp_path / "manifest.json"
    await run_sync_pass(service, local_dir=local_dir, folder_id=None, manifest_path=manifest_path)

    service.docs[doc_id]["content"] = b"v2"
    service.clock += 1
    service.docs[doc_id]["modifiedTime"] = f"t{service.clock}"

    result = await run_sync_pass(service, local_dir=local_dir, folder_id=None, manifest_path=manifest_path)

    assert result.pulled == ["Doc A"]
    assert (local_dir / "Doc A.docx").read_bytes() == b"v2"


async def test_local_only_change_pushes(service, tmp_path):
    service.add_doc("Doc A", b"v1")
    local_dir = tmp_path / "sync"
    manifest_path = tmp_path / "manifest.json"
    await run_sync_pass(service, local_dir=local_dir, folder_id=None, manifest_path=manifest_path)

    (local_dir / "Doc A.docx").write_bytes(b"locally edited")

    result = await run_sync_pass(service, local_dir=local_dir, folder_id=None, manifest_path=manifest_path)

    assert result.pushed == ["Doc A"]
    assert list(service.docs.values())[0]["content"] == b"locally edited"


async def test_conflict_preserves_both_versions(service, tmp_path):
    doc_id = service.add_doc("Doc A", b"v1")
    local_dir = tmp_path / "sync"
    manifest_path = tmp_path / "manifest.json"
    await run_sync_pass(service, local_dir=local_dir, folder_id=None, manifest_path=manifest_path)

    # Change both sides since the last sync.
    (local_dir / "Doc A.docx").write_bytes(b"my local edit")
    service.docs[doc_id]["content"] = b"someone else's remote edit"
    service.clock += 1
    service.docs[doc_id]["modifiedTime"] = f"t{service.clock}"

    result = await run_sync_pass(service, local_dir=local_dir, folder_id=None, manifest_path=manifest_path)

    assert result.conflicts == ["Doc A"]
    # Canonical path now holds the remote version...
    assert (local_dir / "Doc A.docx").read_bytes() == b"someone else's remote edit"
    # ...and the local edit was preserved, not lost, under a conflict-suffixed name.
    conflict_files = list(local_dir.glob("Doc A (conflict *).docx"))
    assert len(conflict_files) == 1
    assert conflict_files[0].read_bytes() == b"my local edit"


async def test_remote_trash_moves_local_file_instead_of_deleting(service, tmp_path):
    doc_id = service.add_doc("Doc A", b"v1")
    local_dir = tmp_path / "sync"
    manifest_path = tmp_path / "manifest.json"
    await run_sync_pass(service, local_dir=local_dir, folder_id=None, manifest_path=manifest_path)

    del service.docs[doc_id]  # simulate trash (drops out of the non-trashed listing)

    result = await run_sync_pass(service, local_dir=local_dir, folder_id=None, manifest_path=manifest_path)

    assert result.remote_deleted == ["Doc A"]
    assert not (local_dir / "Doc A.docx").exists()
    assert (local_dir / sync_engine.DELETED_SUBDIR / "Doc A.docx").read_bytes() == b"v1"
    assert len(load_manifest(manifest_path)) == 0


async def test_local_deletion_self_heals_and_never_touches_remote(service, tmp_path):
    service.add_doc("Doc A", b"v1")
    local_dir = tmp_path / "sync"
    manifest_path = tmp_path / "manifest.json"
    await run_sync_pass(service, local_dir=local_dir, folder_id=None, manifest_path=manifest_path)

    (local_dir / "Doc A.docx").unlink()

    result = await run_sync_pass(service, local_dir=local_dir, folder_id=None, manifest_path=manifest_path)

    # Remote is authoritative and is never mutated because of a local disappearance...
    assert len(service.docs) == 1
    assert list(service.docs.values())[0]["content"] == b"v1"
    # ...and the local copy comes back rather than silently staying gone.
    assert result.untracked_missing_local == ["Doc A"]
    assert (local_dir / "Doc A.docx").read_bytes() == b"v1"
    assert len(load_manifest(manifest_path)) == 1

    # A third pass with nothing further changed must be a clean no-op — the
    # self-heal must not leave the manifest in a state that re-triggers itself.
    third = await run_sync_pass(service, local_dir=local_dir, folder_id=None, manifest_path=manifest_path)
    assert third.pulled == []
    assert third.pushed == []
    assert third.untracked_missing_local == []
    assert len(service.docs) == 1


async def test_new_local_file_is_pushed_as_new_doc(service, tmp_path):
    local_dir = tmp_path / "sync"
    local_dir.mkdir(parents=True)
    manifest_path = tmp_path / "manifest.json"
    (local_dir / "brand-new.txt").write_text("hello from disk")

    result = await run_sync_pass(service, local_dir=local_dir, folder_id=None, manifest_path=manifest_path)

    assert result.pushed == ["brand-new.txt"]
    assert len(service.docs) == 1
    assert list(service.docs.values())[0]["content"] == b"hello from disk"
    manifest = load_manifest(manifest_path)
    assert len(manifest) == 1


async def test_manifest_json_is_never_treated_as_a_syncable_file(service, tmp_path):
    local_dir = tmp_path / "sync"
    local_dir.mkdir(parents=True)
    manifest_path = local_dir / "manifest.json"  # deliberately inside the sync dir
    manifest_path.write_text(json.dumps({"entries": {}}))

    result = await run_sync_pass(service, local_dir=local_dir, folder_id=None, manifest_path=manifest_path)

    assert result.pushed == []
    assert len(service.docs) == 0


async def test_unsupported_local_extension_is_ignored_not_pushed(service, tmp_path):
    local_dir = tmp_path / "sync"
    local_dir.mkdir(parents=True)
    manifest_path = tmp_path / "manifest.json"
    (local_dir / "image.png").write_bytes(b"\x89PNG fake")

    result = await run_sync_pass(service, local_dir=local_dir, folder_id=None, manifest_path=manifest_path)

    assert result.pushed == []
    assert result.errors == []
    assert len(service.docs) == 0


async def test_sync_config_round_trip(tmp_path):
    config_path = tmp_path / "sync_config.json"
    config = SyncConfig(enabled=True, local_dir="C:/sync", folder_id="f1", interval_seconds=120)
    save_config(config_path, config)

    loaded = load_config(config_path)

    assert loaded == config


async def test_load_config_defaults_when_missing(tmp_path):
    loaded = load_config(tmp_path / "does_not_exist.json")
    assert loaded.enabled is False
    assert loaded.local_dir is None
