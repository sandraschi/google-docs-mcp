# Changelog

## [Unreleased]

- Weekly-grant truth (verified live: grant minted 2026-10-10 died `invalid_grant`
  2026-10-17): new `GrantExpiredError`, `grant_expired` on the status shape,
  honest "re-run start_oauth, nothing misconfigured" messaging; Settings +
  Onboarding show amber expired state with Reconnect buttons; ONBOARDING 7-day
  paragraph rewritten (test-user listing does NOT exempt); "once per machine"
  claims fixed; regression test with fake dead grant (6/6 auth tests green)

- Assfix 2026-10-03 (first full pass): `google_shutdown` tool + `GET /api/capabilities`; hermetic OAuth tests (local-client fallback neutralization, conftest autouse fixture); `Resource`→honest-`Any` (50 false pyright errors); Prefab 0.20 compat shims; ExportFormat/upload/oauth/docs-tool typing fixes (pyright 86 → 0); unified dev deps; pre-commit + hook

- Standard-conformance pass (TOOL_DESIGN_STANDARDS.md audit): `browse` now paginates its docs
  list (`limit`/`cursor`/`has_more`/`next_cursor`, matching `list_files`/`search` — folders stay
  unpaginated, bounded at 200); added two new Prefab App tools (`show_google_drive_folder_app`,
  `show_google_docs_sync_status_app`) for the list/status coverage rule; every tool now sets
  `annotations=` (readOnlyHint/destructiveHint/idempotentHint/openWorldHint); `google_docs_sync`
  and `google_docs_convert_advanced` docstrings now lead with `[RATIONALE]` like `google_drive`
  does; added `docs/README.md` index; clarified the webhooks declared-exception note in
  `docs/DEVELOPMENT.md` (it had gone stale — written before the sync feature existed, so it
  claimed "no background jobs" when one now runs).
- `google_drive`: added `browse` (folder-aware listing with breadcrumbs), `backup_folder`
  (export every doc in a folder to local files + `manifest.json`), and `restore_file` (overwrite
  an existing Google Doc's content from a local file) operations.
- New `google_docs_convert_advanced` tool — bridges to a sibling libreoffice-mcp server via a
  real MCP client call for formats Drive's own export can't produce (doc/fodt/rtf). Surfaces
  `error_type: "dependency_unavailable"` when libreoffice-mcp isn't reachable.
- New `google_docs_sync` tool + `sync_engine.py` — polling two-way sync between a local folder
  and a Drive folder (OneDrive-like local mirror). Conflicts are never silently overwritten
  (local edit renamed and kept, Drive becomes canonical); remote trash moves the local file to
  `_remote_deleted/` instead of deleting it; local deletion self-heals via re-pull rather than
  touching the Drive doc. Runs as a background `asyncio` poll loop in the Starlette backend's
  lifespan, minimum 60s interval.
- Webapp: new **Sync** page (`/sync`) — configure/enable/disable the local mirror, run a pass
  on demand, view last-run/last-error status.
- Webapp: Documents page now has a folder browser (breadcrumb navigation, replacing the
  always-flat file list as the default view), a Backup-folder panel, and per-file Restore/
  Convert (advanced) actions.
- `google_drive`: added `export` (pdf/docx/odt/txt/html/rtf/epub, 10 MB Drive API limit) and
  `import_file` (.docx/.odt/.txt/.md/.html/.rtf → new Google Doc) operations, plus matching
  webapp UI on the Documents page (per-file export dropdown, Import button with real upload).
- Webapp: added **Apps Hub** page (`/apps`) — dynamic fleet discovery, probes other running
  fleet webapps from the shared port registry.
- Webapp: added a dedicated **Onboarding wizard** (`/onboarding`) — walks through Google Cloud
  Console setup, lets you paste the OAuth client id/secret (persisted to
  `data/oauth_client.json`, gitignored) without editing `claude_desktop_config.json` directly,
  then triggers the browser consent flow. Dashboard's red CTA now points here instead of
  Settings.
- Fixed: local LLM model selection was picking `models[0]` with no residency check — the exact
  anti-pattern documented as BUG-030 in the fleet bugs depot. Now resident-first: never switches
  away from a model already loaded in Ollama.
- `config.py`: OAuth client id/secret now fall back to a local JSON file when env vars aren't
  set (env vars still win when both are present) — backs the onboarding wizard above.

## [0.1.0] - 2026-09-10

Initial release.

- `google_docs` — Docs API v1 portmanteau (create, get, read_text, get_structure, insert_text,
  append_text, delete_range, replace_all_text, insert_page_break, insert_table,
  update_paragraph_style, update_text_style, batch_update)
- `google_drive` — Drive API v3 portmanteau (list_files, search, get_metadata, create_folder,
  copy, move, rename, trash, untrash, delete_permanently, share, list_permissions,
  revoke_permission, list_revisions, list_comments, add_comment, reply_comment, resolve_comment)
- `google_docs_auth` — OAuth lifecycle (status, start_oauth, revoke)
- `google_docs_mcp_help` — static tool reference
- `show_google_docs_status_app` — Prefab UI status card
- Webapp dashboard (React/Vite/Bun/Tailwind) with catch-them-all pages
- MCPB packaging, Tauri/NSIS desktop installer
- FastMCP 3.4.4, Starlette 1.x backend, uv + justfile build
