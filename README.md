# Runstream

Ingest experiment `meta.json` records into SQLite, expose them over a small **read-only HTTP API**. Built to demonstrate **data pipeline + service** wiring with tests and CI.

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

---

## Docker

```bash
mkdir data
runstream ingest-once fixtures/example_run --db data/runstream.db
docker compose build
docker compose up
```

API listens on port **8000**; the DB file is `./data/runstream.db` mounted at `/data/runstream.db`.

---

## Schema

- JSON Schema: [`schemas/run_record.json`](schemas/run_record.json)
- Example payload: [`fixtures/example_run/meta.json`](fixtures/example_run/meta.json)

---

## Engineering status

| Area | Status |
|------|--------|
| JSON Schema + Pydantic `RunRecord` | Done |
| Ingest: recursive `meta.json`, validate, SHA-256 idempotency | Done |
| SQLite store + tag / project / since filters | Done |
| CLI: `runstream ingest-once`, `runstream serve` | Done |
| FastAPI: `/health`, `/runs`, `/runs/{run_id}` | Done |
| Pytest (ingest + API) | Done |
| GitHub Actions CI | Done |
| Dockerfile + docker-compose | Done |

### Next (Phase 3)

1. **Agent / tools layer**: OpenAI-style tool definitions wrapping `list_runs` / `get_run` (same query layer as API, no shell).
2. **CLI `runstream ask`**: optional LLM backend via env; regression fixtures for expected `run_id` answers.
3. **POST `/runs`**: authenticated ingest through HTTP (same validation as file ingest).

### Later

- File watcher / scheduled ingest
- Rate limits, API key middleware
- Export to Parquet

---

## Layout

```text
src/runstream/
  models.py    # RunRecord
  store.py     # SQLite
  ingest.py    # scan + upsert
  api.py       # FastAPI
  cli.py       # Typer
schemas/run_record.json
tests/
```

---

## License

MIT — see `LICENSE`.
