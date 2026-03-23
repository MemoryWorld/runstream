# Runstream

Ingest experiment `meta.json` into SQLite, expose **GET + POST** HTTP APIs, and optionally drive **OpenAI function-calling** over the same catalog (tools only — **no shell**). Tests + CI on every push.

**Current release: 0.3.0** — Phase 4 complete (watch/cron, hardened auth, rate limit + access logs, Parquet export).

---

## Quickstart

```bash
cd runstream
python -m venv .venv
source .venv/bin/activate   # Windows: .\.venv\Scripts\activate
pip install -e ".[dev]"

# 1) Ingest (scans path for meta.json files)
runstream ingest-once fixtures/example_run --db runstream.db

# 2) API
runstream serve --db runstream.db --port 8000
# GET http://127.0.0.1:8000/health
# GET http://127.0.0.1:8000/runs?tag=onnx-exported
# GET http://127.0.0.1:8000/runs/exp-2026-03-23-a7f3
```

OpenAPI: `http://127.0.0.1:8000/docs`

### POST `/runs` (HTTP ingest)

Same body shape as `meta.json` / `RunRecord`. Idempotent via SHA-256 of canonical JSON.

```bash
curl -s -X POST http://127.0.0.1:8000/runs -H "Content-Type: application/json" -d @fixtures/example_run/meta.json
```

- **Dev (default):** if only `RUNSTREAM_API_KEY` is set, send `Authorization: Bearer <key>` on POST.
- **Production (recommended):** set `RUNSTREAM_REQUIRE_AUTH=1` and **`RUNSTREAM_API_KEY`** — POST without a valid Bearer returns 401/503. Docker Compose enables this by default; override the key via env (see `.env.example`).

### LLM + tools (optional)

```bash
pip install 'runstream[llm]'
export OPENAI_API_KEY=...
runstream ask "Which runs are tagged onnx-exported?" --db runstream.db
runstream tools-json   # dump OpenAI tool definitions
```

### Watch directory (live ingest)

```bash
runstream watch fixtures/example_run --db runstream.db --debounce 2
```

On `meta.json` create/modify under the watched tree, ingest re-runs after **debounce** seconds (default 2). Ctrl+C stops.

### Rate limit & access logs (API)

When **`RUNSTREAM_ENABLE_RATE_LIMIT=1`**, each client IP is limited to **`RUNSTREAM_RATE_LIMIT_RPM`** requests per sliding 60s window (default **120**). `/health`, `/docs`, `/openapi.json`, and `/redoc` are exempt.

With **`runstream serve`**, one-line access logs go to stderr under the logger **`runstream.access`**. Set **`RUNSTREAM_DISABLE_ACCESS_LOG=1`** to turn them off.

### Parquet export

```bash
pip install 'runstream[parquet]'   # or dev extra already includes pyarrow
runstream export-parquet --db runstream.db --out runs.parquet
```

Writes the SQLite `runs` table as Parquet (JSON fields remain JSON strings).

### Cron (scheduled ingest)

`ingest-once` is idempotent; suitable for cron:

```bash
*/15 * * * * cd /path/to/runstream && .venv/bin/runstream ingest-once /data/runs --db /data/runstream.db
```

---

## Docker

```bash
mkdir data
runstream ingest-once fixtures/example_run --db data/runstream.db
export RUNSTREAM_API_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
docker compose build
docker compose up
```

Compose sets **`RUNSTREAM_REQUIRE_AUTH=1`** by default; POST `/runs` needs `Authorization: Bearer $RUNSTREAM_API_KEY`. Copy [`.env.example`](.env.example) to tune variables.

API listens on port **8000**; the DB file is `./data/runstream.db` mounted at `/data/runstream.db`.

---

## Schema

- JSON Schema: [`schemas/run_record.json`](schemas/run_record.json)
- Example payload: [`fixtures/example_run/meta.json`](fixtures/example_run/meta.json)
- Tool regression cases: [`fixtures/regression_tools.json`](fixtures/regression_tools.json)

---

## Engineering status

| Area | Status |
|------|--------|
| JSON Schema + Pydantic `RunRecord` | Done |
| Ingest + `ingest_record()` (shared with POST) | Done |
| SQLite + filters + idempotent upsert | Done |
| CLI: `ingest-once`, **`watch`**, `serve`, **`export-parquet`**, `tools-json`, `ask` | Done |
| Filesystem watch + cron doc | Done |
| FastAPI: `GET /health`, `/runs`, `/runs/{id}`, **`POST /runs`** | Done |
| OpenAI tools: `search_runs`, `get_run` → `tools.py` / `execute_tool` | Done |
| `ask_with_llm` + mock regression test | Done |
| Pytest (CI) | Done |
| GitHub Actions CI | Done |
| Dockerfile + docker-compose | Done |

### Phase 4

1. ~~Watch / cron~~ — **done** (`runstream watch`, cron uses `ingest-once`).
2. ~~Auth default-on~~ — **done**: `RUNSTREAM_REQUIRE_AUTH` + Docker Compose + `.env.example`.
3. ~~Rate limit + access logs~~ — **done**: `RUNSTREAM_ENABLE_RATE_LIMIT`, `RUNSTREAM_RATE_LIMIT_RPM` (default 120), `runstream.access` logs (disable with `RUNSTREAM_DISABLE_ACCESS_LOG=1`).
4. ~~Parquet export~~ — **done**: `runstream export-parquet --db … --out runs.parquet` (`pip install 'runstream[parquet]'`).

### Next / Roadmap (not scheduled)

Ideas for later releases—not a commitment, but so the repo does not read as “finished with nothing left”:

- **Backend scale:** optional PostgreSQL (or a storage abstraction), readiness checks that hit the DB, JSON structured logs for hosted deployments.
- **API & data:** batch ingest or async jobs for large trees; richer filters (metrics ranges, combined queries); Parquet with clearer column layout or partitioning.
- **Product:** minimal web UI for browsing runs; streaming or multi-provider options for `ask`.
- **Hardening:** contract tests against OpenAPI; narrower integration tests for watch/debounce where feasible.

---

## Layout

```text
src/runstream/
  models.py
  store.py
  ingest.py
  tools.py      # OpenAI tool schemas + execute_tool (no shell)
  ask.py        # optional LLM loop
  api.py
  http_middleware.py  # access logs + optional rate limit
  parquet_export.py
  cli.py
  watch_ingest.py
schemas/
fixtures/
tests/
```

---

## License

MIT — see `LICENSE`.
