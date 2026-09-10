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


def test_documents_browse_unconfigured(client, monkeypatch):
    monkeypatch.delenv("GOOGLE_DOCS_MCP_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_DOCS_MCP_CLIENT_SECRET", raising=False)
    resp = client.get("/api/documents/browse")
    assert resp.status_code == 200  # google_drive's dialogic error, not an HTTP error
    assert resp.json()["error_type"] == "not_configured"


def test_documents_backup_requires_output_dir(client, monkeypatch):
    monkeypatch.setenv("GOOGLE_DOCS_MCP_CLIENT_ID", "x")
    monkeypatch.setenv("GOOGLE_DOCS_MCP_CLIENT_SECRET", "y")
    resp = client.post("/api/documents/backup", json={})
    assert resp.status_code == 400
    # configured (env vars set) but no cached token yet -> not_authenticated, not not_configured
    assert resp.json()["error_type"] == "not_authenticated"


def test_document_restore_unconfigured(client, monkeypatch):
    monkeypatch.delenv("GOOGLE_DOCS_MCP_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_DOCS_MCP_CLIENT_SECRET", raising=False)
    resp = client.post("/api/documents/fake-id/restore", json={"file_path": "C:/nope.docx"})
    assert resp.status_code == 400
    assert resp.json()["error_type"] == "not_configured"


def test_document_convert_advanced_unconfigured(client, monkeypatch):
    monkeypatch.delenv("GOOGLE_DOCS_MCP_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_DOCS_MCP_CLIENT_SECRET", raising=False)
    resp = client.post(
        "/api/documents/fake-id/convert-advanced",
        json={"output_format": "doc", "output_path": "C:/out.doc"},
    )
    assert resp.status_code == 400
    assert resp.json()["error_type"] == "not_configured"


@pytest.fixture(autouse=True)
def _isolated_sync_paths(monkeypatch, tmp_path):
    """Every sync REST test must never touch this repo's real data/ directory."""
    monkeypatch.setenv("GOOGLE_DOCS_MCP_SYNC_CONFIG_PATH", str(tmp_path / "sync_config.json"))
    monkeypatch.setenv("GOOGLE_DOCS_MCP_SYNC_MANIFEST_PATH", str(tmp_path / "sync_manifest.json"))


def test_sync_status_before_configure(client):
    resp = client.get("/api/sync/status")
    assert resp.status_code == 200
    body = resp.json()
    assert body["data"]["config"]["local_dir"] is None
    assert body["data"]["last_run"] is None


def test_sync_configure_then_status(client, tmp_path):
    resp = client.post("/api/sync/configure", json={"local_dir": str(tmp_path / "mirror")})
    assert resp.status_code == 200
    assert resp.json()["data"]["local_dir"] == str(tmp_path / "mirror")

    status = client.get("/api/sync/status").json()
    assert status["data"]["config"]["local_dir"] == str(tmp_path / "mirror")


def test_sync_enable_requires_prior_configure(client):
    resp = client.post("/api/sync/enable")
    assert resp.status_code == 400
    assert resp.json()["error_type"] == "validation"


def test_sync_enable_disable_round_trip(client, tmp_path):
    client.post("/api/sync/configure", json={"local_dir": str(tmp_path / "mirror")})
    enabled = client.post("/api/sync/enable")
    assert enabled.status_code == 200
    assert enabled.json()["data"]["enabled"] is True

    disabled = client.post("/api/sync/disable")
    assert disabled.status_code == 200
    assert disabled.json()["data"]["enabled"] is False


def test_sync_run_once_without_configure(client):
    resp = client.post("/api/sync/run-once")
    assert resp.status_code == 400
    assert resp.json()["error_type"] == "validation"


def test_sync_run_once_unconfigured_oauth_updates_last_error(client, monkeypatch, tmp_path):
    monkeypatch.delenv("GOOGLE_DOCS_MCP_CLIENT_ID", raising=False)
    monkeypatch.delenv("GOOGLE_DOCS_MCP_CLIENT_SECRET", raising=False)
    client.post("/api/sync/configure", json={"local_dir": str(tmp_path / "mirror")})

    resp = client.post("/api/sync/run-once")

    assert resp.status_code == 400
    assert resp.json()["error_type"] == "not_configured"
