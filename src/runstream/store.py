from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import RunRecord

SCHEMA = """
CREATE TABLE IF NOT EXISTS runs (
    run_id TEXT PRIMARY KEY,
    project TEXT NOT NULL,
    started_at TEXT NOT NULL,
    status TEXT NOT NULL,
    metrics_json TEXT NOT NULL,
    config_ref TEXT,
    artifacts_json TEXT NOT NULL,
    tags_json TEXT NOT NULL,
    source_path TEXT,
    raw_hash TEXT NOT NULL,
    ingested_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_runs_project ON runs(project);
CREATE INDEX IF NOT EXISTS idx_runs_started ON runs(started_at);
"""


def connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    conn.commit()
    return conn


def upsert_run(
    conn: sqlite3.Connection,
    record: RunRecord,
    source_path: str | None,
    raw_hash: str,
) -> str:
    """Returns 'inserted' | 'updated' | 'unchanged'."""
    now = datetime.now(timezone.utc).isoformat()
    cur = conn.execute("SELECT raw_hash FROM runs WHERE run_id = ?", (record.run_id,))
    row = cur.fetchone()
    if row is not None and row["raw_hash"] == raw_hash:
        return "unchanged"
    action = "updated" if row is not None else "inserted"
    conn.execute(
        """
        INSERT INTO runs (
            run_id, project, started_at, status, metrics_json, config_ref,
            artifacts_json, tags_json, source_path, raw_hash, ingested_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(run_id) DO UPDATE SET
            project = excluded.project,
            started_at = excluded.started_at,
            status = excluded.status,
            metrics_json = excluded.metrics_json,
            config_ref = excluded.config_ref,
            artifacts_json = excluded.artifacts_json,
            tags_json = excluded.tags_json,
            source_path = excluded.source_path,
            raw_hash = excluded.raw_hash,
            ingested_at = excluded.ingested_at
        """,
        (
            record.run_id,
            record.project,
            record.started_at.isoformat(),
            record.status,
            json.dumps(record.metrics, sort_keys=True),
            record.config_ref,
            json.dumps(record.artifacts, sort_keys=True),
            json.dumps(record.tags),
            source_path,
            raw_hash,
            now,
        ),
    )
    conn.commit()
    return action


@dataclass
class ListRunsResult:
    items: list[dict[str, Any]]
    total: int


def list_runs(
    conn: sqlite3.Connection,
    *,
    limit: int = 50,
    offset: int = 0,
    project: str | None = None,
    tag: str | None = None,
    since: str | None = None,
) -> ListRunsResult:
    where: list[str] = []
    params: list[Any] = []
    if project:
        where.append("project = ?")
        params.append(project)
    if since:
        where.append("started_at >= ?")
        params.append(since)
    if tag:
        where.append(
            "EXISTS (SELECT 1 FROM json_each(runs.tags_json) WHERE json_each.value = ?)"
        )
        params.append(tag)
    wh = (" WHERE " + " AND ".join(where)) if where else ""
    count_sql = f"SELECT COUNT(*) FROM runs{wh}"
    total = conn.execute(count_sql, params).fetchone()[0]
    sql = f"SELECT * FROM runs{wh} ORDER BY started_at DESC LIMIT ? OFFSET ?"
    params_ext = [*params, limit, offset]
    rows = conn.execute(sql, params_ext).fetchall()
    items = [_row_to_api(dict(r)) for r in rows]
    return ListRunsResult(items=items, total=total)


def get_run(conn: sqlite3.Connection, run_id: str) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    if row is None:
        return None
    return _row_to_api(dict(row))


def _row_to_api(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "run_id": row["run_id"],
        "project": row["project"],
        "started_at": row["started_at"],
        "status": row["status"],
        "metrics": json.loads(row["metrics_json"]),
        "config_ref": row["config_ref"],
        "artifacts": json.loads(row["artifacts_json"]),
        "tags": json.loads(row["tags_json"]),
        "source_path": row["source_path"],
        "raw_hash": row["raw_hash"],
        "ingested_at": row["ingested_at"],
    }
