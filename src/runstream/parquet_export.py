from __future__ import annotations

from pathlib import Path

from .store import connect


def export_runs_parquet(db_path: Path, out_path: Path) -> int:
    """
    Dump the `runs` table to Parquet (raw SQLite column layout: JSON as strings).
    Requires optional dependency: pip install 'runstream[parquet]'.
    """
    try:
        import pyarrow as pa
        import pyarrow.parquet as pq
    except ImportError as e:  # pragma: no cover - exercised when pyarrow missing
        raise SystemExit(
            "Parquet export needs pyarrow. Install: pip install 'runstream[parquet]'"
        ) from e

    conn = connect(db_path)
    try:
        cur = conn.execute("SELECT * FROM runs ORDER BY started_at DESC")
        col_names = [c[0] for c in cur.description]
        rows = cur.fetchall()
        if not rows:
            table = pa.table(
                {c: pa.array([], type=pa.string()) for c in col_names}
            )
        else:
            data = {col: [r[col] for r in rows] for col in col_names}
            table = pa.table(data)
        out_path = out_path.resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        pq.write_table(table, out_path)
        return len(rows)
    finally:
        conn.close()
