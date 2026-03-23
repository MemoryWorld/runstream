# Runstream

Ingest experiment `meta.json` into SQLite, expose **GET + POST** HTTP APIs, and optionally drive **OpenAI function-calling** over the same catalog (tools only — **no shell**). Tests + CI on every push.

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

If `RUNSTREAM_API_KEY` is set, send `Authorization: Bearer <key>`.

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
docker compose build
docker compose up
```

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
| CLI: `ingest-once`, **`watch`**, `serve`, `tools-json`, `ask` | Done |
| Filesystem watch + cron doc | Done |
| FastAPI: `GET /health`, `/runs`, `/runs/{id}`, **`POST /runs`** | Done |
| OpenAI tools: `search_runs`, `get_run` → `tools.py` / `execute_tool` | Done |
| `ask_with_llm` + mock regression test | Done |
| Pytest (18 tests) | Done |
| GitHub Actions CI | Done |
| Dockerfile + docker-compose | Done |

### Phase 4 (in progress)

1. ~~Watch / cron~~ — **done** (`runstream watch`, cron uses `ingest-once`).
2. **Auth default-on** — next: `RUNSTREAM_REQUIRE_AUTH` + compose defaults.
3. **Rate limit + access logs** — then.
4. **Parquet export** — then.

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
  cli.py
  watch_ingest.py
schemas/
fixtures/
tests/
```

---

## License

MIT — see `LICENSE`.
