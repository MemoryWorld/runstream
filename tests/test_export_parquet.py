from pathlib import Path

import pyarrow.parquet as pq

from runstream.ingest import ingest_path
from runstream.parquet_export import export_runs_parquet


def test_export_parquet_roundtrip(tmp_path: Path) -> None:
    db = tmp_path / "t.db"
    ingest_path(Path("fixtures/example_run"), db)
    out = tmp_path / "runs.parquet"
    n = export_runs_parquet(db, out)
    assert n >= 1
    assert out.is_file()
    table = pq.read_table(out)
    assert "run_id" in table.column_names
    assert table.num_rows == n


def test_export_parquet_empty_db(tmp_path: Path) -> None:
    db = tmp_path / "empty.db"
    db.touch()
    from runstream.store import connect

    connect(db).close()
    out = tmp_path / "empty.parquet"
    n = export_runs_parquet(db, out)
    assert n == 0
    t = pq.read_table(out)
    assert t.num_rows == 0
