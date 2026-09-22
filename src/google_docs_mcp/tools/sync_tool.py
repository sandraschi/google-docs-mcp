"""google_docs_sync — configure and run polling two-way sync between a local
folder and a Google Drive folder.

[RATIONALE] This is deliberately a *separate* tool from `google_drive`, not
another operation on it: sync has its own persistent state (a config file
and a manifest tracking every synced doc's last-known hash/modifiedTime)
that every other `google_drive` operation is stateless with respect to.
Mixing "list files" and "reconcile two trees of files with conflict
detection" under one portmanteau would make the tool's contract far harder
to reason about. See `google_docs_mcp.sync_engine` for the actual reconcile
logic and its safety defaults (conflicts never silently overwritten, remote
deletes never delete local files, local deletes never trash remote docs).
"""

from __future__ import annotations

import os
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Any, Literal

from googleapiclient.errors import HttpError
from pydantic import Field

from google_docs_mcp.config import data_dir
from google_docs_mcp.google_client import get_drive_service, http_error_to_dict
from google_docs_mcp.oauth import NotAuthenticatedError, NotConfiguredError
from google_docs_mcp.sync_engine import SyncConfig, load_config, load_manifest, run_sync_pass, save_config

SyncOperation = Literal["configure", "status", "run_once", "enable", "disable"]


def sync_config_path() -> Path:
    """Live (env-overridable) path — read fresh each call, same pattern as
    `config.Settings` properties, so tests can isolate state via monkeypatch
    without writing into this repo's real `data/` directory. `data_dir()`
    resolves to %LOCALAPPDATA%\\{identifier}\\data in the frozen Tauri app
    (not the wiped-on-exit _MEIPASS temp dir) — see config.py."""
    return Path(os.getenv("GOOGLE_DOCS_MCP_SYNC_CONFIG_PATH", str(data_dir() / "sync_config.json")))


def sync_manifest_path() -> Path:
    return Path(os.getenv("GOOGLE_DOCS_MCP_SYNC_MANIFEST_PATH", str(data_dir() / "sync_manifest.json")))


def _not_ready(exc: NotConfiguredError | NotAuthenticatedError) -> dict[str, Any]:
    is_configured_issue = isinstance(exc, NotConfiguredError)
    return {
        "success": False,
        "error": str(exc),
        "error_type": "not_configured" if is_configured_issue else "not_authenticated",
        "suggestions": (
            ["See docs/ONBOARDING.md to create a Google Cloud OAuth client."]
            if is_configured_issue
            else ["Call google_docs_auth(operation='start_oauth') first."]
        ),
    }


async def google_docs_sync(
    operation: Annotated[
        SyncOperation,
        Field(description="Which sync operation to run. See docstring Operations table."),
    ],
    local_dir: Annotated[
        str | None, Field(description="Local folder to sync. Required for: configure.")
    ] = None,
    folder_id: Annotated[
        str | None,
        Field(description="Drive folder to sync (omit/None for Drive root). Optional for: configure."),
    ] = None,
    interval_seconds: Annotated[
        int,
        Field(
            description="Background poll interval in seconds, minimum 60. Optional for: configure. "
            "Default 300 (5 minutes)."
        ),
    ] = 300,
    export_format: Annotated[
        Literal["docx", "odt", "txt", "html"],
        Field(
            description="Local file format for docs pulled from Drive. Optional for: configure. Default docx."
        ),
    ] = "docx",
) -> dict[str, Any]:
    """[RATIONALE] A dedicated tool, not another `google_drive` operation — sync carries
    persistent state (a config file and a manifest tracking every synced doc's last-known
    hash/modifiedTime) that every `google_drive` operation is stateless with respect to. It is
    also **polling**, not push-based: a publicly reachable HTTPS endpoint for Drive's
    `files.watch` push notifications isn't realistic for a local desktop app with no public
    endpoint, so this reconciles on an interval instead (see `sync_engine.py` module docstring
    for the full tradeoff and the three safety defaults: conflicts never silently overwritten,
    remote deletes never delete local files, local deletes never trash remote docs).

    Configure, inspect, or manually trigger the local-folder <-> Drive-folder sync.

    ## Operations
    - configure(local_dir, folder_id?, interval_seconds?, export_format?) — set up (or replace) the
      sync pair. Does **not** enable background polling by itself — call `enable` too.
    - status() — current config, whether background polling is active, and how many docs are tracked
    - run_once() — run exactly one reconcile pass right now, synchronously, and return what happened
    - enable() — turn on background polling at `interval_seconds` (requires `configure` first)
    - disable() — turn off background polling (config and manifest are kept, not deleted)

    ## Return Format
    On success: `{"success": true, "message": str, "data": {...}}`. `run_once`'s `data` is
    `{"pulled": [name, ...], "pushed": [...], "conflicts": [...], "remote_deleted": [...],
    "untracked_missing_local": [...], "errors": [{"name", "error"}], "ran_at": iso8601}`.
    On failure: `{"success": false, "error": str, "error_type": str, "suggestions": [str]}`.

    ## Examples
    ```python
    await google_docs_sync(operation="configure", local_dir="C:/Users/me/GoogleDocsSync",
                            folder_id="1AbC...", interval_seconds=600)
    await google_docs_sync(operation="enable")
    await google_docs_sync(operation="run_once")
    await google_docs_sync(operation="status")
    ```

    Notes:
    - This is **polling** sync, not instant push-based sync (see module docstring for why) —
      changes appear after the next pass, at most `interval_seconds` later.
    - Conflicts (both sides changed since the last sync) are never silently overwritten: the local
      edit is renamed with a timestamp suffix and kept; Drive's version becomes the file's content
      going forward.
    - A file deleted locally does **not** delete the Drive document — it self-heals by being
      re-pulled on the next pass (Drive is authoritative). A document trashed on Drive does
      **not** delete the local file — it's moved to a `_remote_deleted` subfolder instead.
    """
    if operation == "configure":
        if not local_dir:
            return {"success": False, "error": "local_dir is required", "error_type": "validation"}
        config = SyncConfig(
            enabled=False,
            local_dir=local_dir,
            folder_id=folder_id,
            interval_seconds=max(60, interval_seconds),
            export_format=export_format,
        )
        save_config(sync_config_path(), config)
        return {
            "success": True,
            "message": f"Sync configured for {local_dir}. Call operation='enable' to start background polling.",
            "data": asdict(config),
        }

    if operation == "status":
        config = load_config(sync_config_path())
        manifest = load_manifest(sync_manifest_path())
        return {
            "success": True,
            "message": f"{'Enabled' if config.enabled else 'Disabled'}, {len(manifest)} doc(s) tracked.",
            "data": {"config": asdict(config), "tracked_count": len(manifest)},
        }

    if operation == "enable":
        config = load_config(sync_config_path())
        if not config.local_dir:
            return {
                "success": False,
                "error": "No sync configured yet",
                "error_type": "validation",
                "suggestions": ["Call operation='configure' with local_dir first."],
            }
        config.enabled = True
        save_config(sync_config_path(), config)
        return {"success": True, "message": "Background sync enabled.", "data": asdict(config)}

    if operation == "disable":
        config = load_config(sync_config_path())
        config.enabled = False
        save_config(sync_config_path(), config)
        return {"success": True, "message": "Background sync disabled.", "data": asdict(config)}

    if operation == "run_once":
        config = load_config(sync_config_path())
        if not config.local_dir:
            return {
                "success": False,
                "error": "No sync configured yet",
                "error_type": "validation",
                "suggestions": ["Call operation='configure' with local_dir first."],
            }
        try:
            service = get_drive_service()
        except (NotConfiguredError, NotAuthenticatedError) as exc:
            return _not_ready(exc)
        try:
            result = await run_sync_pass(
                service,
                local_dir=Path(config.local_dir),
                folder_id=config.folder_id,
                manifest_path=sync_manifest_path(),
                export_format=config.export_format,
            )
        except HttpError as exc:
            return http_error_to_dict(exc)
        return {
            "success": True,
            "message": (
                f"Sync pass complete: {len(result.pulled)} pulled, {len(result.pushed)} pushed, "
                f"{len(result.conflicts)} conflict(s), {len(result.errors)} error(s)."
            ),
            "data": result.as_dict(),
        }

    return {"success": False, "error": f"Unknown operation '{operation}'", "error_type": "validation"}
