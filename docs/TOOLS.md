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

## `google_docs_mcp_help()`

Static markdown reference of the tool surface. No network calls, no parameters.

## `show_google_docs_status_app()`

Prefab UI card (`@mcp.tool(app=True)`) — renders auth/config state in-chat. Same underlying
data as `google_docs_auth(operation="status")`, presented as a rich card instead of a dict.

## Return shape (all tools)

Success: `{"success": true, "message": str, "data": {...}}`
Failure: `{"success": false, "error": str, "error_type": str, "suggestions": [str]}`

`error_type` values: `not_configured`, `not_authenticated`, `validation`, `permission`,
`not_found`, `conflict`, `rate_limited`, `api_error`.
