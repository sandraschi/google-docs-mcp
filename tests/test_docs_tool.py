"""Unit tests for google_docs — all Google API calls are mocked (see conftest.py)."""

from __future__ import annotations

from googleapiclient.errors import HttpError

from google_docs_mcp.tools.docs_tool import google_docs


class FakeResp:
    def __init__(self, status: int):
        self.status = status
        self.reason = "Not Found"


async def test_create_requires_title(configured_env, mock_docs_service):
    result = await google_docs(operation="create", title=None)
    assert result["success"] is False
    assert result["error_type"] == "validation"


async def test_create_success(configured_env, mock_docs_service):
    mock_docs_service.documents().create().execute.return_value = {"documentId": "abc123"}
    result = await google_docs(operation="create", title="My Doc")
    assert result["success"] is True
    assert result["data"]["document_id"] == "abc123"
    assert result["data"]["url"] == "https://docs.google.com/document/d/abc123/edit"


async def test_read_text_extracts_paragraphs(configured_env, mock_docs_service):
    doc = {
        "body": {
            "content": [
                {
                    "paragraph": {
                        "elements": [{"textRun": {"content": "Hello "}}, {"textRun": {"content": "world.\n"}}]
                    }
                }
            ]
        }
    }
    mock_docs_service.documents().get().execute.return_value = doc
    result = await google_docs(operation="read_text", document_id="abc123")
    assert result["success"] is True
    assert result["data"]["text"] == "Hello world.\n"


async def test_get_structure_extracts_headings(configured_env, mock_docs_service):
    doc = {
        "body": {
            "content": [
                {
                    "startIndex": 1,
                    "endIndex": 10,
                    "paragraph": {
                        "paragraphStyle": {"namedStyleType": "HEADING_1"},
                        "elements": [{"textRun": {"content": "Intro\n"}}],
                    },
                }
            ]
        }
    }
    mock_docs_service.documents().get().execute.return_value = doc
    result = await google_docs(operation="get_structure", document_id="abc123")
    assert result["success"] is True
    outline = result["data"]["outline"]
    assert len(outline) == 1
    assert outline[0]["style"] == "HEADING_1"
    assert outline[0]["text"] == "Intro"


async def test_append_text_fetches_end_index(configured_env, mock_docs_service):
    mock_docs_service.documents().get().execute.return_value = {"body": {"content": [{"endIndex": 42}]}}
    mock_docs_service.documents().batchUpdate().execute.return_value = {"replies": [{}]}
    result = await google_docs(operation="append_text", document_id="abc123", text="more text")
    assert result["success"] is True
    assert result["data"]["index"] == 41


async def test_delete_range_requires_bounds(configured_env, mock_docs_service):
    result = await google_docs(operation="delete_range", document_id="abc123", start_index=None)
    assert result["success"] is False
    assert result["error_type"] == "validation"


async def test_replace_all_text_reports_occurrences(configured_env, mock_docs_service):
    mock_docs_service.documents().batchUpdate().execute.return_value = {
        "replies": [{"replaceAllText": {"occurrencesChanged": 3}}]
    }
    result = await google_docs(
        operation="replace_all_text", document_id="abc123", find_text="{{x}}", replace_text="y"
    )
    assert result["success"] is True
    assert result["data"]["occurrences_changed"] == 3


async def test_update_text_style_requires_an_attribute(configured_env, mock_docs_service):
    result = await google_docs(
        operation="update_text_style", document_id="abc123", start_index=1, end_index=5
    )
    assert result["success"] is False
    assert result["error_type"] == "validation"


async def test_http_error_maps_to_dialogic_shape(configured_env, mock_docs_service):
    mock_docs_service.documents().get().execute.side_effect = HttpError(FakeResp(404), b"not found")
    result = await google_docs(operation="get", document_id="missing")
    assert result["success"] is False
    assert result["error_type"] == "not_found"
    assert result["suggestions"]


async def test_not_configured_short_circuits_before_any_api_call(monkeypatch):
    monkeypatch.delenv("GOOGLE_DOCS_MCP_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_DOCS_MCP_CLIENT_SECRET", raising=False)

    # get_docs_service() is NOT mocked here — it must raise NotConfiguredError
    # itself (via require_credentials()) before any googleapiclient.build() call.
    result = await google_docs(operation="create", title="X")
    assert result["success"] is False
    assert result["error_type"] == "not_configured"
