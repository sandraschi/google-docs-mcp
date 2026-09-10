---
name: google-docs-expert
description: How to drive google-docs-mcp — Google Docs content editing and Google Drive file lifecycle via three portmanteau tools.
---

# google-docs-mcp usage guide

This server gives an agent real read/write access to a user's Google Docs and
Drive, through three tools:

- **`google_docs_auth`** — OAuth lifecycle (status / start_oauth / revoke).
- **`google_docs`** — Docs API v1 content editing (create, read, edit text and styles).
- **`google_drive`** — Drive API v3 file lifecycle (list, search, share, trash, comments).

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

Never retry `not_configured` or `validation` errors without changing the call —
they will fail identically every time.
