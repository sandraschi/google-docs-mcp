# Changelog

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
