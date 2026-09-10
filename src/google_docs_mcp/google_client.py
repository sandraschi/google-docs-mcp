"""Thin wrapper around the googleapiclient `discovery.build()` calls.

Kept separate from the tool modules so tests can monkeypatch `get_docs_service`
/ `get_drive_service` without touching OAuth or network code.
"""

from __future__ import annotations

from typing import Any

from googleapiclient.discovery import Resource, build
from googleapiclient.errors import HttpError

from google_docs_mcp.oauth import require_credentials


def get_docs_service() -> Resource:
    creds = require_credentials()
    return build("docs", "v1", credentials=creds, cache_discovery=False)


def get_drive_service() -> Resource:
    creds = require_credentials()
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def http_error_to_dict(exc: HttpError) -> dict[str, Any]:
    """Map a googleapiclient HttpError into the fleet dialogic error shape."""
    status = exc.resp.status if exc.resp is not None else None
    reason = str(exc)
    error_type = {
        400: "validation",
        401: "auth",
        403: "permission",
        404: "not_found",
        409: "conflict",
        429: "rate_limited",
    }.get(status, "api_error")

    suggestions = {
        "auth": [
            "Run google_docs_auth(operation='start_oauth') to re-authenticate.",
        ],
        "permission": [
            "Confirm the signed-in Google account has access to this file.",
            "Ask the file owner to share it with your account first.",
        ],
        "not_found": [
            "Double-check the document_id / file_id.",
            "Use google_drive(operation='search', query=...) to find the correct id.",
        ],
        "rate_limited": [
            "Wait a few seconds and retry — Google Docs/Drive API has per-minute quotas.",
        ],
    }.get(error_type, ["Check the request parameters and retry."])

    return {
        "success": False,
        "error": reason,
        "error_type": error_type,
        "status_code": status,
        "suggestions": suggestions,
    }
