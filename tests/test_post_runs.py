from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from runstream.api import app
from runstream.ingest import ingest_path

VALID_BODY = {
    "run_id": "post-test-1",
    "project": "api-ingest",
    "started_at": "2026-03-24T10:00:00Z",
    "status": "completed",
    "metrics": {"loss": 1.0},
    "config_ref": "cfg.yaml",
    "artifacts": {"ckpt": "x.pt"},
    "tags": ["from-post"],
}


@pytest.fixture
def client_empty_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    db = tmp_path / "p.db"
    monkeypatch.setenv("RUNSTREAM_DB", str(db))
    return TestClient(app)


def test_post_run_insert(client_empty_db: TestClient) -> None:
    r = client_empty_db.post("/runs", json=VALID_BODY)
    assert r.status_code == 200
    assert r.json()["action"] == "inserted"
    g = client_empty_db.get("/runs/post-test-1")
    assert g.status_code == 200
    assert g.json()["project"] == "api-ingest"


def test_post_run_idempotent(client_empty_db: TestClient) -> None:
    client_empty_db.post("/runs", json=VALID_BODY)
    r2 = client_empty_db.post("/runs", json=VALID_BODY)
    assert r2.status_code == 200
    assert r2.json()["action"] == "unchanged"


def test_post_run_requires_bearer_when_key_set(
    client_empty_db: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RUNSTREAM_API_KEY", "secret-token")
    r = client_empty_db.post(
        "/runs",
        json={
            **VALID_BODY,
            "run_id": "auth-test",
        },
    )
    assert r.status_code == 401
    r2 = client_empty_db.post(
        "/runs",
        json={
            **VALID_BODY,
            "run_id": "auth-test",
        },
        headers={"Authorization": "Bearer secret-token"},
    )
    assert r2.status_code == 200


def test_post_run_validation_error(client_empty_db: TestClient) -> None:
    bad = {**VALID_BODY, "status": "not-a-status"}
    r = client_empty_db.post("/runs", json=bad)
    assert r.status_code == 422


def test_post_run_require_auth_without_key_misconfigured(
    client_empty_db: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("RUNSTREAM_REQUIRE_AUTH", "1")
    monkeypatch.delenv("RUNSTREAM_API_KEY", raising=False)
    r = client_empty_db.post("/runs", json={**VALID_BODY, "run_id": "misconfig-1"})
    assert r.status_code == 503
