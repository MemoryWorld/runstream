from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from .store import connect, get_run, list_runs

app = FastAPI(title="Runstream", version="0.1.0")


def _db_path() -> Path:
    return Path(os.environ.get("RUNSTREAM_DB", "runstream.db")).resolve()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/runs")
def runs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    project: str | None = None,
    tag: str | None = None,
    since: str | None = None,
) -> JSONResponse:
    conn = connect(_db_path())
    try:
        result = list_runs(
            conn, limit=limit, offset=offset, project=project, tag=tag, since=since
        )
        return JSONResponse(
            {"items": result.items, "total": result.total, "limit": limit, "offset": offset}
        )
    finally:
        conn.close()


@app.get("/runs/{run_id}")
def run_detail(run_id: str) -> dict:
    conn = connect(_db_path())
    try:
        row = get_run(conn, run_id)
        if row is None:
            raise HTTPException(status_code=404, detail="run not found")
        return row
    finally:
        conn.close()
