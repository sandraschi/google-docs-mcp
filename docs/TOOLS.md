# Tool Reference

## `google_docs_auth(operation)`

OAuth lifecycle for Docs/Drive access.

| operation | Params | Notes |
|---|---|---|
| `status` | — | Read-only. Returns `configured`, `authenticated`, `scopes`, `token_path`, `expiry`. |
| `start_oauth` | — | **Opens the user's browser.** Blocks until consent completes or is abandoned. |
| `revoke` | — | Deletes the cached token file. |

## `google_docs(operation, ...)`

Google Docs API v1 content editing.

| operation | Required params | Optional params |
|---|---|---|
| `create` | `title` | — |
| `get` | `document_id` | — |
| `read_text` | `document_id` | — |
| `get_structure` | `document_id` | — |
| `insert_text` | `document_id`, `text` | `index` |
| `append_text` | `document_id`, `text` | — |
| `delete_range` | `document_id`, `start_index`, `end_index` | — |
| `replace_all_text` | `document_id`, `find_text`, `replace_text` | `match_case` |
| `insert_page_break` | `document_id`, `index` | — |
| `insert_table` | `document_id`, `rows`, `columns`, `index` | — |
| `update_paragraph_style` | `document_id`, `start_index`, `end_index` | `alignment`, `named_style_type` |
| `update_text_style` | `document_id`, `start_index`, `end_index` | `bold`, `italic`, `underline`, `font_size`, `foreground_color` |
| `batch_update` | `document_id`, `requests` | — (raw Docs API request list) |

## `google_drive(operation, ...)`

Google Drive API v3 file lifecycle.

| operation | Required params | Optional params |
|---|---|---|
| `list_files` | — | `folder_id`, `docs_only`, `limit`, `cursor` |
| `search` | `query` | `folder_id`, `docs_only`, `limit`, `cursor` |
| `get_metadata` | `file_id` | — |
| `create_folder` | `name` | `folder_id` |
| `copy` | `file_id` | `name`, `folder_id` |
| `move` | `file_id`, `new_parent_id` | — |
| `rename` | `file_id`, `name` | — |
| `trash` | `file_id` | — |
| `untrash` | `file_id` | — |
| `delete_permanently` | `file_id`, `confirm=True` | — |
| `share` | `file_id`, `email` | `role`, `send_notification` |
| `list_permissions` | `file_id` | — |
| `revoke_permission` | `file_id`, `permission_id` | — |
| `list_revisions` | `file_id` | `limit`, `cursor` |
| `list_comments` | `file_id` | `limit`, `cursor` |
| `add_comment` | `file_id`, `content` | — |
| `reply_comment` | `file_id`, `comment_id`, `content` | — |
| `resolve_comment` | `file_id`, `comment_id` | — |
| `export` | `file_id`, `output_path` | `export_format` (pdf/docx/odt/txt/html/rtf/epub, default pdf) |
| `import_file` | `file_path` | `name`, `folder_id` |
| `browse` | — | `folder_id` (Drive root if omitted), `limit`, `cursor` — folders + docs directly inside, plus breadcrumbs. Folders are unpaginated (bounded, 200 max); the docs list is paginated like `list_files`/`search` (`has_more`/`next_cursor` in `data`) |
| `backup_folder` | `output_dir` | `folder_id`, `export_format` (default pdf), `recursive` — exports every doc in a folder to local files + writes `manifest.json` |
| `restore_file` | `file_id`, `file_path` | — overwrites an **existing** Google Doc's content from a local file (inverse of `export`/`import_file`, which create new docs) |

## `google_docs_convert_advanced(file_id, output_format, output_path)`

Bridges to [libreoffice-mcp](../../libreoffice-mcp) via a real MCP client call for output formats
Google Drive's native `export` can't produce (`doc`, `fodt`, `rtf`). Exports the doc to a temp
docx via `google_drive(operation="export")`, then calls libreoffice-mcp's `convert` operation.
Returns `error_type: "dependency_unavailable"` (distinct from this server's own
`not_configured`/`not_authenticated`) when libreoffice-mcp isn't reachable at
`LIBREOFFICE_MCP_URL` (default `http://127.0.0.1:10981/mcp`).

| Param | Required | Notes |
|---|---|---|
| `file_id` | Yes | Google Doc to convert |
| `output_format` | Yes | One of `doc`, `fodt`, `rtf`, `odt`, `txt`, `pdf`, `html` |
| `output_path` | Yes | Local destination for the converted file |

## `google_docs_sync(operation, ...)`

Configure, inspect, or manually trigger a polling two-way sync between a local folder and a
Drive folder — like OneDrive Desktop, but checked on an interval rather than pushed instantly.
See [`sync_engine.py`](../src/google_docs_mcp/sync_engine.py) for the reconcile algorithm and
its safety defaults (conflicts never silently overwritten, remote deletes never delete local
files, local deletes never trash remote docs).

| operation | Required params | Optional params |
|---|---|---|
| `configure` | `local_dir` | `folder_id` (Drive root if omitted), `interval_seconds` (default 300, min 60), `export_format` (docx/odt/txt/html, default docx) |
| `status` | — | Current config, whether background polling is active, tracked doc count |
| `run_once` | — | Runs exactly one reconcile pass synchronously, returns what happened |
| `enable` | — | Turns on background polling at `interval_seconds` (requires `configure` first) |
| `disable` | — | Turns off background polling (config and manifest are kept, not deleted) |

Polling is **not** instant — changes appear after the next pass, at most `interval_seconds`
later. A file deleted locally does not delete the Drive document (self-heals by re-pull next
pass); a document trashed on Drive does not delete the local file (moved to `_remote_deleted/`
instead); a file changed on both sides is a conflict (local edit renamed with a timestamp
suffix and kept, Drive's version becomes canonical).

## `google_docs_stitch(operation, ...)`
Stitcher: `preview` lists candidate sources (recent N, search, or ids) for
free; `stitch` exports them as text, dedupes, and writes a NEW Google Doc
with titled sections + source links. The iPad flow (many small saved docs →
one compendium) automated behind one button — see the Stitcher webapp page
and `POST /api/stitch[/preview]`.

## `google_docs_mcp_help()`

Static markdown reference of the tool surface. No network calls, no parameters.

## `show_google_docs_status_app()`

Prefab UI card (`@mcp.tool(app=True)`) — renders auth/config state in-chat. Same underlying
data as `google_docs_auth(operation="status")`, presented as a rich card instead of a dict.

## `show_google_drive_folder_app(folder_id?)`

Prefab UI card — renders a Drive folder's contents (subfolders + docs) as tables with
breadcrumbs. Same underlying data as `google_drive(operation="browse", folder_id=...)`.

## `show_google_docs_sync_status_app()`

Prefab UI card — renders the local-folder sync configuration and status. Same underlying data
as `google_docs_sync(operation="status")`.

## Tool annotation hints

Every tool sets `annotations=` (`readOnlyHint`/`destructiveHint`/`idempotentHint`/
`openWorldHint`) on its `@mcp.tool()` registration in `server.py`, per
TOOL_DESIGN_STANDARDS.md §9. For portmanteau tools mixing read/write/destructive operations,
the hint reflects the worst case present — e.g. `google_drive` sets `destructiveHint=True`
because it includes `delete_permanently`, even though most of its operations are non-destructive.

## Return shape (all tools)

Success: `{"success": true, "message": str, "data": {...}}`
Failure: `{"success": false, "error": str, "error_type": str, "suggestions": [str]}`

`error_type` values: `not_configured`, `not_authenticated`, `validation`, `permission`,
`not_found`, `conflict`, `rate_limited`, `api_error`, `dependency_unavailable`
(`google_docs_convert_advanced` only — libreoffice-mcp not reachable).
