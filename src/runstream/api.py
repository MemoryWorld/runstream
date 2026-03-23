from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Header, Query
from fastapi.responses import JSONResponse

from .http_middleware import AccessLogMiddleware, RateLimitMiddleware
from .ingest import ingest_record
from .models import RunRecord
from .store import connect, get_run, list_runs

app = FastAPI(title="Runstream", version="0.2.0")
app.add_middleware(RateLimitMiddleware)
app.add_middleware(AccessLogMiddleware)


def _db_path() -> Path:
    return Path(os.environ.get("RUNSTREAM_DB", "runstream.db")).resolve()


def _env_truthy(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in ("1", "true", "yes", "on")


def _require_write_auth(authorization: str | None) -> None:
    expected = os.environ.get("RUNSTREAM_API_KEY")
    require = _env_truthy("RUNSTREAM_REQUIRE_AUTH")
    if require:
        if not expected:
            raise HTTPException(
                status_code=503,
                detail="RUNSTREAM_API_KEY must be set when RUNSTREAM_REQUIRE_AUTH=1",
            )
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(status_code=401, detail="Authorization Bearer token required")
        token = authorization[7:].strip()
        if token != expected:
            raise HTTPException(status_code=403, detail="invalid token")
        return
    if not expected:
        return
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Authorization Bearer token required")
    token = authorization[7:].strip()
    if token != expected:
        raise HTTPException(status_code=403, detail="invalid token")


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


@app.post("/runs")
def create_run(
    record: RunRecord,
    authorization: str | None = Header(None, alias="Authorization"),
) -> dict:
    """
    Upsert a run (same validation + idempotency as file ingest).
    If `RUNSTREAM_REQUIRE_AUTH=1`, Bearer token is **always** required and `RUNSTREAM_API_KEY` must be set.
    Otherwise, if only `RUNSTREAM_API_KEY` is set, Bearer is required for POST.
    """
    _require_write_auth(authorization)
    action = ingest_record(record, _db_path(), source_path=None)
    return {"run_id": record.run_id, "action": action}
