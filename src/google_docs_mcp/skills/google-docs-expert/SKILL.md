---
name: google-docs-expert
description: How to drive google-docs-mcp — Google Docs content editing, Google Drive file lifecycle, folder browsing/backup, LibreOffice format conversion, and local-folder sync.
---

# google-docs-mcp usage guide

This server gives an agent real read/write access to a user's Google Docs and
Drive, through nine tools:

- **`google_docs_auth`** — OAuth lifecycle (status / start_oauth / revoke).
- **`google_docs`** — Docs API v1 content editing (create, read, edit text and styles).
- **`google_drive`** — Drive API v3 file lifecycle (list, search, share, trash, comments,
  folder browsing, folder backup, restore).
- **`google_docs_convert_advanced`** — format conversion via a sibling libreoffice-mcp server
  (doc/fodt/rtf, formats Drive's own export can't produce).
- **`google_docs_sync`** — polling two-way sync between a local folder and a Drive folder.
- **`google_docs_mcp_help`** — static reference, no network calls.
- **`show_google_docs_status_app`** / **`show_google_drive_folder_app`** /
  **`show_google_docs_sync_status_app`** — Prefab in-chat cards for auth status, a folder
  listing, and sync status respectively. Same data as the plain-dict tools they mirror
  (`google_docs_auth(status)`, `google_drive(browse)`, `google_docs_sync(status)`) — use these
  when the host renders MCP Apps and a rich card adds value; the plain-dict tools remain the
  right choice for programmatic chaining (e.g. taking a `file_id` from `browse`'s output and
  passing it to `google_docs`).

## First call of a session

Always call `google_docs_auth(operation="status")` before anything else. If
`authenticated` is `false`:

- If `configured` is also `false`, the user has not set up a Google Cloud
  OAuth client yet — point them at `docs/ONBOARDING.md`, do not attempt
  `start_oauth` (it will fail with a clear `not_configured` error).
- If `configured` is `true` but `authenticated` is `false`, call
  `google_docs_auth(operation="start_oauth")` — **tell the user a browser
  window is about to open** before calling it; this operation blocks until
  they finish (or abandon) the Google consent screen.

## Editing workflow

1. Find or create the target document:
   - New doc: `google_docs(operation="create", title="...")` → returns `document_id`.
   - Existing doc: `google_drive(operation="search", query="...")` → pick a `file_id`
     from `data.items` (that `id` is the same value as `document_id`).
2. Read before you write when the edit needs context:
   - `google_docs(operation="read_text", document_id=...)` for plain text.
   - `google_docs(operation="get_structure", document_id=...)` for a heading/paragraph
     outline with index ranges — use this to find *where* to insert or restyle.
3. **Indices shift after every edit.** Never reuse an index from before a prior
   `insert_text`/`delete_range`/`insert_table` call in the same turn — re-fetch
   `get_structure` (or track the returned `index`/length) before the next edit.
4. Prefer `append_text` over `insert_text` with a guessed index when the goal is
   simply "add this at the end" — it re-fetches the true end index internally.
5. For find/replace across a whole document (templating, boilerplate swaps), use
   `replace_all_text` rather than manual index math.
6. For anything not covered by a named operation (nested lists, footnotes, headers/
   footers, embedded images by URL, suggested-edit mode), use
   `google_docs(operation="batch_update", requests=[...])` with a raw Docs API
   `batchUpdate` request list — see https://developers.google.com/docs/api/reference/rest/v1/documents/request
   for the full request catalog.

## File lifecycle

- `trash` is reversible; `delete_permanently` is **not** and requires
  `confirm=True` — default to `trash` unless the user explicitly says "permanently"
  or "forever".
- `share` defaults to `role="reader"` — always confirm the intended role
  (reader / commenter / writer) with the user before sharing, especially before
  granting `writer`.
- Pagination (`list_files`, `search`, `list_revisions`, `list_comments`): pass
  `cursor` from a previous response's `data.next_cursor` to continue; stop when
  `data.has_more` is `false`.

## Comments

Google Docs comments are a Drive API concept, not a Docs API one — use
`google_drive(operation="list_comments" | "add_comment" | "reply_comment" |
"resolve_comment", ...)`. `resolve_comment` posts a reply with
`action: "resolve"`, matching how the Docs UI's "Resolve" button behaves.

## Export and import

- `google_drive(operation="export", file_id=..., export_format="pdf"|"docx"|"odt"|"txt"|"html"|
  "rtf"|"epub", output_path=...)` downloads a Google Doc to a local file. Drive API's export
  endpoint has a **10 MB** output limit — for a very long document, export as `txt`/`html`
  (smaller) rather than `pdf`/`docx`, or suggest splitting the document.
- `google_drive(operation="import_file", file_path=..., name?, folder_id?)` uploads a local
  `.docx`/`.odt`/`.txt`/`.md`/`.html`/`.rtf` file and converts it into a new Google Doc. A `.md`
  source is imported as literal plain text (Drive has no Markdown renderer) — if the user wants
  real Docs formatting from Markdown, import it then apply `google_docs` style operations
  (`update_paragraph_style` for headings, etc.) as a follow-up.

## Folder browsing and backup

- `google_drive(operation="browse", folder_id?)` lists the folders and Google Docs directly
  inside `folder_id` (Drive root if omitted), plus breadcrumbs back to root — use this to let a
  user navigate their Drive folder structure rather than only flat `search`.
- `google_drive(operation="backup_folder", output_dir=..., folder_id?, export_format="pdf",
  recursive=False)` exports every doc in a folder to local files and writes a `manifest.json`
  alongside them. Use `recursive=True` only when the user asks for subfolders too — a large,
  deeply nested Drive folder can mean a lot of API calls.
- `google_drive(operation="restore_file", file_id=..., file_path=...)` overwrites an **existing**
  Google Doc's content from a local file — this is destructive to the doc's current content (no
  undo beyond Drive's own revision history). Confirm with the user before calling it, same as
  any other content-replacing operation.

## LibreOffice conversion

`google_docs_convert_advanced(file_id=..., output_format=..., output_path=...)` reaches formats
Drive's native `export` can't produce (`doc`, `fodt`, `rtf`) by calling a sibling libreoffice-mcp
server. If that server isn't running, the call fails with `error_type: "dependency_unavailable"`
— tell the user libreoffice-mcp needs to be started, don't confuse this with `not_configured`
(this server's own OAuth setup) or retry it blindly.

## Local folder sync

`google_docs_sync` sets up a OneDrive-like local mirror of a Drive folder, checked on an
interval rather than instantly:

1. `configure(local_dir=..., folder_id?, interval_seconds=300, export_format="docx")` — always
   ask the user for the local folder path explicitly; don't guess one.
2. `enable()` to start background polling, or `run_once()` to run a single pass immediately and
   show the user what happened.
3. `status()` to check whether it's enabled and how many docs are tracked.

This is polling, not instant, sync — set expectations with the user accordingly. Conflicts
(changed on both sides) are never silently resolved: the local edit is kept under a renamed
filename and Drive's version becomes canonical going forward — tell the user this happened and
where the renamed file is, don't just report success.

## Error handling

Every tool call returns `{"success": false, "error": ..., "error_type": ...,
"suggestions": [...]}` on failure. Read `error_type` before retrying:

| error_type | Meaning | What to do |
|---|---|---|
| `not_configured` | OAuth client never set up | Point the user at `docs/ONBOARDING.md` |
| `not_authenticated` | No valid cached token | Call `google_docs_auth(operation="start_oauth")` |
| `validation` | Missing/bad parameter | Fix the call, do not retry blindly |
| `permission` | Signed-in account lacks access | Ask the file owner to share it |
| `not_found` | Bad document_id/file_id | Re-search via `google_drive(operation="search", ...)` |
| `rate_limited` | Google API quota hit | Wait a few seconds, retry once |
| `dependency_unavailable` | libreoffice-mcp not reachable (`google_docs_convert_advanced` only) | Tell the user to start libreoffice-mcp |

Never retry `not_configured` or `validation` errors without changing the call —
they will fail identically every time.
