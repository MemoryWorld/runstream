from __future__ import annotations

import json
from pathlib import Path

import pytest

from runstream.ingest import ingest_path, load_record
from runstream.store import connect, get_run


def test_load_fixture_example(tmp_path: Path) -> None:
    src = Path("fixtures/example_run/meta.json")
    rec = load_record(src)
    assert rec.run_id == "exp-2026-03-23-a7f3"
    assert "onnx-exported" in rec.tags


def test_ingest_idempotent(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    root = Path("fixtures/example_run")
    a = ingest_path(root, db)
    assert a["inserted"] == 1
    b = ingest_path(root, db)
    assert b["unchanged"] == 1
    assert b["inserted"] == 0
    conn = connect(db)
    try:
        row = get_run(conn, "exp-2026-03-23-a7f3")
        assert row is not None
        assert row["project"] == "tiny-lm-baseline"
    finally:
        conn.close()


def test_ingest_invalid_json_skipped(tmp_path: Path) -> None:
    d = tmp_path / "bad"
    d.mkdir()
    (d / "meta.json").write_text("{not json", encoding="utf-8")
    stats = ingest_path(d, tmp_path / "x.db")
    assert stats["errors"] == 1
    assert stats["inserted"] == 0


def test_ingest_invalid_status_skipped(tmp_path: Path) -> None:
    d = tmp_path / "bad2"
    d.mkdir()
    (d / "meta.json").write_text(
        json.dumps(
            {
                "run_id": "x",
                "project": "p",
                "started_at": "2026-01-01T00:00:00Z",
                "status": "bogus",
                "metrics": {},
                "artifacts": {},
                "tags": [],
            }
        ),
        encoding="utf-8",
    )
    stats = ingest_path(d, tmp_path / "y.db")
    assert stats["errors"] == 1
