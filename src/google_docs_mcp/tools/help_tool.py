"""google_docs_mcp_help — static tool-surface reference, no network calls."""

from __future__ import annotations

from typing import Any

HELP_TEXT = """# google-docs-mcp tool reference

## google_docs_auth(operation)
OAuth lifecycle: status | start_oauth | revoke.

## google_docs(operation, ...)
Docs API v1 content editing: create | get | read_text | get_structure |
insert_text | append_text | delete_range | replace_all_text |
insert_page_break | insert_table | update_paragraph_style |
update_text_style | batch_update.

## google_drive(operation, ...)
Drive API v3 file lifecycle: list_files | search | get_metadata |
create_folder | copy | move | rename | trash | untrash |
delete_permanently | share | list_permissions | revoke_permission |
list_revisions | list_comments | add_comment | reply_comment |
resolve_comment.

## Typical flow
1. google_docs_auth(operation="start_oauth")   — once per machine
2. google_docs(operation="create", title="...")
3. google_docs(operation="append_text", document_id=..., text="...")
4. google_drive(operation="share", file_id=..., email="...", role="writer")

Full reference: docs/TOOLS.md. Onboarding (OAuth client setup): docs/ONBOARDING.md.
"""


async def google_docs_mcp_help() -> dict[str, Any]:
    """Return a compact reference of every tool and operation this server exposes.

    ## Return Format
    `{"success": true, "message": str, "data": {"help": str}}` — `help` is markdown, bounded
    (single fixed page, no pagination needed).

    ## Examples
    ```python
    await google_docs_mcp_help()
    ```
    """
    return {"success": True, "message": "Tool reference.", "data": {"help": HELP_TEXT}}
