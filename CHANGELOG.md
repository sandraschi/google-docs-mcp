# Changelog

## [Unreleased]

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
