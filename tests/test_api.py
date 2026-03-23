from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from runstream.api import app
from runstream.ingest import ingest_path


@pytest.fixture
def client_with_db(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TestClient:
    db = tmp_path / "api.db"
    ingest_path(Path("fixtures/example_run"), db)
    monkeypatch.setenv("RUNSTREAM_DB", str(db))
    return TestClient(app)


def test_health(client_with_db: TestClient) -> None:
    r = client_with_db.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_list_runs(client_with_db: TestClient) -> None:
    r = client_with_db.get("/runs")
    assert r.status_code == 200
    body = r.json()
    assert body["total"] == 1
    assert len(body["items"]) == 1


def test_list_runs_tag_filter(client_with_db: TestClient) -> None:
    r = client_with_db.get("/runs", params={"tag": "onnx-exported"})
    assert r.json()["total"] == 1
    r2 = client_with_db.get("/runs", params={"tag": "nope"})
    assert r2.json()["total"] == 0


def test_get_run(client_with_db: TestClient) -> None:
    r = client_with_db.get("/runs/exp-2026-03-23-a7f3")
    assert r.status_code == 200
    assert r.json()["metrics"]["final_loss"] == 2.36


def test_get_run_404(client_with_db: TestClient) -> None:
    r = client_with_db.get("/runs/missing")
    assert r.status_code == 404
