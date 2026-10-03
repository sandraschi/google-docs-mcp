"""google_docs — the Docs API v1 portmanteau tool.

[RATIONALE] Google Docs API v1 exposes document editing exclusively through
one `documents.batchUpdate` endpoint taking a list of typed request objects
(insertText, deleteContentRange, updateTextStyle, ...). Wrapping each request
type as its own MCP tool would mean 12+ near-identical tools that all do the
same HTTP call with a different payload shape — the definition of "tool
explosion" the fleet portmanteau pattern exists to prevent (see
TOOL_DESIGN_STANDARDS.md §1). Instead, one `operation` enum selects the
request builder, and `batch_update` remains available as an escape hatch for
any Docs API request shape this wrapper does not special-case yet.
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from googleapiclient.errors import HttpError
from pydantic import Field

from google_docs_mcp.google_client import get_docs_service, http_error_to_dict
from google_docs_mcp.oauth import NotAuthenticatedError, NotConfiguredError

DocsOperation = Literal[
    "create",
    "get",
    "read_text",
    "get_structure",
    "insert_text",
    "append_text",
    "delete_range",
    "replace_all_text",
    "insert_page_break",
    "insert_table",
    "update_paragraph_style",
    "update_text_style",
    "batch_update",
]


def _not_ready(exc: NotConfiguredError | NotAuthenticatedError) -> dict[str, Any]:
    is_configured_issue = isinstance(exc, NotConfiguredError)
    return {
        "success": False,
        "error": str(exc),
        "error_type": "not_configured" if is_configured_issue else "not_authenticated",
        "suggestions": (
            [
                "See docs/ONBOARDING.md to create a Google Cloud OAuth client and set "
                "GOOGLE_DOCS_MCP_CLIENT_ID / GOOGLE_DOCS_MCP_CLIENT_SECRET."
            ]
            if is_configured_issue
            else ["Call google_docs_auth(operation='start_oauth') first."]
        ),
    }


def _extract_text(document: dict[str, Any]) -> str:
    out: list[str] = []
    for element in document.get("body", {}).get("content", []):
        paragraph = element.get("paragraph")
        if not paragraph:
            continue
        for el in paragraph.get("elements", []):
            run = el.get("textRun")
            if run:
                out.append(run.get("content", ""))
    return "".join(out)


def _end_index(document: dict[str, Any]) -> int:
    content = document.get("body", {}).get("content", [])
    if not content:
        return 1
    return content[-1].get("endIndex", 1)


def _extract_structure(document: dict[str, Any]) -> list[dict[str, Any]]:
    outline: list[dict[str, Any]] = []
    for element in document.get("body", {}).get("content", []):
        paragraph = element.get("paragraph")
        if not paragraph:
            continue
        style = paragraph.get("paragraphStyle", {}).get("namedStyleType", "")
        text = "".join(r.get("textRun", {}).get("content", "") for r in paragraph.get("elements", [])).strip()
        if not text:
            continue
        outline.append(
            {
                "start_index": element.get("startIndex"),
                "end_index": element.get("endIndex"),
                "style": style or "NORMAL_TEXT",
                "text": text[:200],
            }
        )
    return outline


def _text_style_fields(
    bold: bool | None,
    italic: bool | None,
    underline: bool | None,
    font_size: float | None,
    foreground_color: str | None,
) -> tuple[dict[str, Any], str]:
    style: dict[str, Any] = {}
    fields: list[str] = []
    if bold is not None:
        style["bold"] = bold
        fields.append("bold")
    if italic is not None:
        style["italic"] = italic
        fields.append("italic")
    if underline is not None:
        style["underline"] = underline
        fields.append("underline")
    if font_size is not None:
        style["fontSize"] = {"magnitude": font_size, "unit": "PT"}
        fields.append("fontSize")
    if foreground_color is not None:
        r = int(foreground_color[0:2], 16) / 255
        g = int(foreground_color[2:4], 16) / 255
        b = int(foreground_color[4:6], 16) / 255
        style["foregroundColor"] = {"color": {"rgbColor": {"red": r, "green": g, "blue": b}}}
        fields.append("foregroundColor")
    return style, ",".join(fields)


async def google_docs(
    operation: Annotated[
        DocsOperation,
        Field(description="Which Docs API operation to run. See docstring Operations table."),
    ],
    document_id: Annotated[
        str | None,
        Field(description="Target document id. Required for every operation except 'create'."),
    ] = None,
    title: Annotated[str | None, Field(description="Doc title. Required for: create.")] = None,
    text: Annotated[
        str | None, Field(description="Text to insert/append. Required for: insert_text, append_text.")
    ] = None,
    index: Annotated[
        int | None,
        Field(
            description="1-based document index to insert/break/table at. Required for: insert_text, "
            "insert_page_break, insert_table. Omit on append_text (always appends at document end)."
        ),
    ] = None,
    start_index: Annotated[
        int | None,
        Field(
            description="Range start (inclusive). Required for: delete_range, update_paragraph_style, "
            "update_text_style."
        ),
    ] = None,
    end_index: Annotated[
        int | None,
        Field(
            description="Range end (exclusive). Required for: delete_range, update_paragraph_style, "
            "update_text_style."
        ),
    ] = None,
    find_text: Annotated[
        str | None, Field(description="Text to search for. Required for: replace_all_text.")
    ] = None,
    replace_text: Annotated[
        str | None, Field(description="Replacement text. Required for: replace_all_text.")
    ] = None,
    match_case: Annotated[
        bool, Field(description="Case-sensitive match for replace_all_text. Default False.")
    ] = False,
    rows: Annotated[int | None, Field(description="Table row count. Required for: insert_table.")] = None,
    columns: Annotated[
        int | None, Field(description="Table column count. Required for: insert_table.")
    ] = None,
    alignment: Annotated[
        Literal["START", "CENTER", "END", "JUSTIFIED"] | None,
        Field(description="Paragraph alignment. Optional for: update_paragraph_style."),
    ] = None,
    named_style_type: Annotated[
        str | None,
        Field(
            description="Paragraph named style, e.g. 'HEADING_1', 'HEADING_2', 'NORMAL_TEXT', 'TITLE'. "
            "Optional for: update_paragraph_style."
        ),
    ] = None,
    bold: Annotated[bool | None, Field(description="Optional for: update_text_style.")] = None,
    italic: Annotated[bool | None, Field(description="Optional for: update_text_style.")] = None,
    underline: Annotated[bool | None, Field(description="Optional for: update_text_style.")] = None,
    font_size: Annotated[
        float | None, Field(description="Point size. Optional for: update_text_style.")
    ] = None,
    foreground_color: Annotated[
        str | None,
        Field(description="6-digit hex, e.g. 'FF0000'. Optional for: update_text_style."),
    ] = None,
    requests: Annotated[
        list[dict[str, Any]] | None,
        Field(description="Raw Docs API batchUpdate request list. Required for: batch_update."),
    ] = None,
) -> dict[str, Any]:
    """[RATIONALE] Portmanteau over the Google Docs API v1 `documents` resource — one
    tool, one `operation` enum, instead of 12+ near-identical batchUpdate wrappers.

    ## Operations
    - create(title) — new blank document, returns document_id + url
    - get(document_id) — full raw Docs API document JSON
    - read_text(document_id) — plain-text body (paragraphs concatenated)
    - get_structure(document_id) — outline: headings/paragraphs with index ranges and style
    - insert_text(document_id, text, index) — insert at a specific index
    - append_text(document_id, text) — insert at the current document end
    - delete_range(document_id, start_index, end_index) — remove a range
    - replace_all_text(document_id, find_text, replace_text, match_case) — find/replace across the doc
    - insert_page_break(document_id, index)
    - insert_table(document_id, rows, columns, index)
    - update_paragraph_style(document_id, start_index, end_index, alignment, named_style_type)
    - update_text_style(document_id, start_index, end_index, bold, italic, underline, font_size,
      foreground_color)
    - batch_update(document_id, requests) — raw passthrough for any Docs API request shape not
      covered above (dry-run short-circuit is not applicable here; this always calls the API)

    ## Return Format
    On success: `{"success": true, "message": str, "data": {...}}`. `data` shape depends on
    operation — `create`/all editing ops return `{"document_id": str, "url": str}` (plus
    `"replies": [...]` for batch_update); `get` returns `{"document": {...raw...}}`; `read_text`
    returns `{"text": str}`; `get_structure` returns `{"outline": [{"start_index", "end_index",
    "style", "text"}]}`.
    On failure: `{"success": false, "error": str, "error_type": str, "suggestions": [str]}`.
    `error_type` is one of `not_configured`, `not_authenticated`, `validation`, `permission`,
    `not_found`, `conflict`, `rate_limited`, `api_error`.

    ## Examples
    ```python
    await google_docs(operation="create", title="Q3 Report")
    await google_docs(operation="append_text", document_id="1AbC...", text="\\nNew paragraph.")
    await google_docs(operation="replace_all_text", document_id="1AbC...",
                       find_text="{{name}}", replace_text="Sandra")
    await google_docs(operation="update_text_style", document_id="1AbC...",
                       start_index=1, end_index=10, bold=True, foreground_color="1155CC")
    ```

    Notes:
    - Requires OAuth first — call `google_docs_auth(operation="start_oauth")` once per machine.
    - Indices are UTF-16 code unit offsets into the document body, as returned by `get`/
      `get_structure` — always re-fetch indices after an edit, since they shift.
    """
    try:
        service = get_docs_service()
    except (NotConfiguredError, NotAuthenticatedError) as exc:
        return _not_ready(exc)

    try:
        if operation == "create":
            if not title:
                return {"success": False, "error": "title is required for create", "error_type": "validation"}
            doc = service.documents().create(body={"title": title}).execute()
            doc_id = doc["documentId"]
            return {
                "success": True,
                "message": f"Created document '{title}'.",
                "data": {"document_id": doc_id, "url": f"https://docs.google.com/document/d/{doc_id}/edit"},
            }

        if not document_id:
            return {"success": False, "error": "document_id is required", "error_type": "validation"}

        if operation == "get":
            doc = service.documents().get(documentId=document_id).execute()
            return {"success": True, "message": f"Fetched document {document_id}.", "data": {"document": doc}}

        if operation == "read_text":
            doc = service.documents().get(documentId=document_id).execute()
            return {
                "success": True,
                "message": "Extracted document text.",
                "data": {"text": _extract_text(doc)},
            }

        if operation == "get_structure":
            doc = service.documents().get(documentId=document_id).execute()
            return {
                "success": True,
                "message": "Extracted document outline.",
                "data": {"outline": _extract_structure(doc)},
            }

        if operation in {"insert_text", "append_text"}:
            if not text:
                return {"success": False, "error": "text is required", "error_type": "validation"}
            target_index = index
            if operation == "append_text" or target_index is None:
                doc = service.documents().get(documentId=document_id).execute()
                target_index = max(_end_index(doc) - 1, 1)
            reqs = [{"insertText": {"location": {"index": target_index}, "text": text}}]
            resp = service.documents().batchUpdate(documentId=document_id, body={"requests": reqs}).execute()
            return {
                "success": True,
                "message": f"Inserted {len(text)} characters at index {target_index}.",
                "data": {
                    "document_id": document_id,
                    "index": target_index,
                    "replies": resp.get("replies", []),
                },
            }

        if operation == "delete_range":
            if start_index is None or end_index is None:
                return {
                    "success": False,
                    "error": "start_index and end_index are required",
                    "error_type": "validation",
                }
            reqs = [{"deleteContentRange": {"range": {"startIndex": start_index, "endIndex": end_index}}}]
            service.documents().batchUpdate(documentId=document_id, body={"requests": reqs}).execute()
            return {
                "success": True,
                "message": f"Deleted range [{start_index}, {end_index}).",
                "data": {"document_id": document_id},
            }

        if operation == "replace_all_text":
            if not find_text or replace_text is None:
                return {
                    "success": False,
                    "error": "find_text and replace_text are required",
                    "error_type": "validation",
                }
            reqs = [
                {
                    "replaceAllText": {
                        "containsText": {"text": find_text, "matchCase": match_case},
                        "replaceText": replace_text,
                    }
                }
            ]
            resp = service.documents().batchUpdate(documentId=document_id, body={"requests": reqs}).execute()
            occurrences = resp.get("replies", [{}])[0].get("replaceAllText", {}).get("occurrencesChanged", 0)
            return {
                "success": True,
                "message": f"Replaced {occurrences} occurrence(s) of '{find_text}'.",
                "data": {"document_id": document_id, "occurrences_changed": occurrences},
            }

        if operation == "insert_page_break":
            if index is None:
                return {"success": False, "error": "index is required", "error_type": "validation"}
            reqs = [{"insertPageBreak": {"location": {"index": index}}}]
            service.documents().batchUpdate(documentId=document_id, body={"requests": reqs}).execute()
            return {"success": True, "message": f"Inserted page break at index {index}.", "data": {}}

        if operation == "insert_table":
            if not rows or not columns or index is None:
                return {
                    "success": False,
                    "error": "rows, columns and index are required",
                    "error_type": "validation",
                }
            reqs = [{"insertTable": {"rows": rows, "columns": columns, "location": {"index": index}}}]
            service.documents().batchUpdate(documentId=document_id, body={"requests": reqs}).execute()
            return {
                "success": True,
                "message": f"Inserted {rows}x{columns} table at index {index}.",
                "data": {"document_id": document_id},
            }

        if operation == "update_paragraph_style":
            if start_index is None or end_index is None:
                return {
                    "success": False,
                    "error": "start_index and end_index are required",
                    "error_type": "validation",
                }
            style: dict[str, Any] = {}
            fields: list[str] = []
            if alignment:
                style["alignment"] = alignment
                fields.append("alignment")
            if named_style_type:
                style["namedStyleType"] = named_style_type
                fields.append("namedStyleType")
            if not fields:
                return {
                    "success": False,
                    "error": "provide at least one of alignment / named_style_type",
                    "error_type": "validation",
                }
            reqs = [
                {
                    "updateParagraphStyle": {
                        "range": {"startIndex": start_index, "endIndex": end_index},
                        "paragraphStyle": style,
                        "fields": ",".join(fields),
                    }
                }
            ]
            service.documents().batchUpdate(documentId=document_id, body={"requests": reqs}).execute()
            return {
                "success": True,
                "message": f"Updated paragraph style [{start_index}, {end_index}).",
                "data": {"document_id": document_id},
            }

        if operation == "update_text_style":
            if start_index is None or end_index is None:
                return {
                    "success": False,
                    "error": "start_index and end_index are required",
                    "error_type": "validation",
                }
            style, text_fields = _text_style_fields(bold, italic, underline, font_size, foreground_color)
            if not text_fields:
                return {
                    "success": False,
                    "error": "provide at least one style attribute (bold/italic/underline/font_size/"
                    "foreground_color)",
                    "error_type": "validation",
                }
            reqs = [
                {
                    "updateTextStyle": {
                        "range": {"startIndex": start_index, "endIndex": end_index},
                        "textStyle": style,
                        "fields": text_fields,
                    }
                }
            ]
            service.documents().batchUpdate(documentId=document_id, body={"requests": reqs}).execute()
            return {
                "success": True,
                "message": f"Updated text style [{start_index}, {end_index}).",
                "data": {"document_id": document_id},
            }

        if operation == "batch_update":
            if not requests:
                return {"success": False, "error": "requests is required", "error_type": "validation"}
            resp = (
                service.documents().batchUpdate(documentId=document_id, body={"requests": requests}).execute()
            )
            return {
                "success": True,
                "message": f"Applied {len(requests)} raw request(s).",
                "data": {"document_id": document_id, "replies": resp.get("replies", [])},
            }

        return {"success": False, "error": f"Unknown operation '{operation}'", "error_type": "validation"}

    except HttpError as exc:
        return http_error_to_dict(exc)
