"""Unit tests for the Starlette webapp backend — via TestClient, no real sockets."""

from __future__ import annotations

import pytest
from starlette.testclient import TestClient

from google_docs_mcp.backend.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health(client):
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_apps_hub_returns_available_flag(client):
    resp = client.get("/api/apps")
    assert resp.status_code == 200
    body = resp.json()
    assert "available" in body
    assert "items" in body


def test_document_export_unconfigured(client, monkeypatch):
    monkeypatch.delenv("GOOGLE_DOCS_MCP_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_DOCS_MCP_CLIENT_SECRET", raising=False)
    resp = client.get("/api/documents/fake-id/export")
    assert resp.status_code == 400
    assert resp.json()["error_type"] == "not_configured"


def test_document_export_rejects_unsupported_format(client, monkeypatch):
    monkeypatch.setenv("GOOGLE_DOCS_MCP_CLIENT_ID", "x")
    monkeypatch.setenv("GOOGLE_DOCS_MCP_CLIENT_SECRET", "y")
    resp = client.get("/api/documents/fake-id/export?format=exe")
    assert resp.status_code == 400


def test_document_import_requires_file(client, monkeypatch):
    monkeypatch.setenv("GOOGLE_DOCS_MCP_CLIENT_ID", "x")
    monkeypatch.setenv("GOOGLE_DOCS_MCP_CLIENT_SECRET", "y")
    resp = client.post("/api/documents/import", data={"name": "no file here"})
    assert resp.status_code == 400
    assert resp.json()["error_type"] == "validation"


def test_document_import_unconfigured(client, monkeypatch):
    monkeypatch.delenv("GOOGLE_DOCS_MCP_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_DOCS_MCP_CLIENT_SECRET", raising=False)
    resp = client.post("/api/documents/import", files={"file": ("notes.txt", b"hello")})
    assert resp.status_code == 400
    assert resp.json()["error_type"] == "not_configured"


def test_onboarding_client_requires_both_fields(client):
    resp = client.post("/api/onboarding/client", json={"client_id": "only-id"})
    assert resp.status_code == 400
    assert resp.json()["error_type"] == "validation"


def test_onboarding_client_write_then_status_reflects_it(client, monkeypatch, tmp_path):
    monkeypatch.delenv("GOOGLE_DOCS_MCP_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_DOCS_MCP_CLIENT_SECRET", raising=False)
    monkeypatch.setenv("GOOGLE_DOCS_MCP_LOCAL_CONFIG_PATH", str(tmp_path / "oauth_client.json"))

    resp = client.post(
        "/api/onboarding/client", json={"client_id": "wizard-id", "client_secret": "wizard-secret"}
    )
    assert resp.status_code == 200
    assert resp.json()["data"]["configured"] is True
    assert resp.json()["data"]["client_source"] == "onboarding_wizard"

    status = client.get("/api/auth/status").json()
    assert status["configured"] is True

    resp = client.delete("/api/onboarding/client")
    assert resp.status_code == 200
    assert resp.json()["cleared"] is True
    assert client.get("/api/auth/status").json()["configured"] is False
