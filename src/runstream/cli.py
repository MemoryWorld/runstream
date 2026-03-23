from __future__ import annotations

from pathlib import Path

import typer
import uvicorn

from .ask import ask_with_llm
from .ingest import ingest_path
from .parquet_export import export_runs_parquet
from .tools import openai_tools_json
from .watch_ingest import watch_and_ingest

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command("ingest-once")
def ingest_once(
    path: Path = typer.Argument(..., exists=True, help="File or directory to scan for meta.json"),
    db: Path = typer.Option(Path("runstream.db"), "--db", help="SQLite database path"),
) -> None:
    """Scan for meta.json files and upsert into SQLite."""
    stats = ingest_path(path, db)
    typer.echo(f"ingest complete -> {db}: {stats}")


@app.command("export-parquet")
def export_parquet_cmd(
    out: Path = typer.Option(..., "--out", help="Output .parquet file path"),
    db: Path = typer.Option(Path("runstream.db"), "--db", help="SQLite database path"),
) -> None:
    """Export all rows from the runs table to Parquet (requires pip install 'runstream[parquet]')."""
    n = export_runs_parquet(db, out)
    typer.echo(f"exported {n} rows -> {out}")


@app.command("watch")
def watch_cmd(
    path: Path = typer.Argument(..., exists=True, help="Directory (or file under a directory) to watch"),
    db: Path = typer.Option(Path("runstream.db"), "--db", help="SQLite database path"),
    debounce: float = typer.Option(2.0, "--debounce", help="Seconds to wait after last change before ingest"),
) -> None:
    """Watch filesystem and re-run ingest after meta.json changes (debounced)."""
    watch_and_ingest(path, db, debounce_sec=debounce)


@app.command("serve")
def serve(
    db: Path = typer.Option(Path("runstream.db"), "--db", help="SQLite database path"),
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port"),
) -> None:
    """Run HTTP API (FastAPI + uvicorn)."""
    import logging
    import os

    os.environ["RUNSTREAM_DB"] = str(db.resolve())
    access = logging.getLogger("runstream.access")
    if not access.handlers:
        _h = logging.StreamHandler()
        _h.setFormatter(logging.Formatter("%(levelname)s [access] %(message)s"))
        access.addHandler(_h)
    access.setLevel(logging.INFO)
    uvicorn.run(
        "runstream.api:app",
        host=host,
        port=port,
        factory=False,
    )


@app.command("tools-json")
def tools_json_cmd() -> None:
    """Print OpenAI-compatible tool definitions (function calling)."""
    typer.echo(openai_tools_json())


@app.command("ask")
def ask_cmd(
    question: str = typer.Argument(..., help="Natural-language question (uses LLM + catalog tools)"),
    db: Path = typer.Option(Path("runstream.db"), "--db", help="SQLite database path"),
    model: str | None = typer.Option(None, "--model", help="Override OPENAI_MODEL"),
) -> None:
    """Query the catalog via OpenAI tool calls (requires OPENAI_API_KEY and pip install 'runstream[llm]')."""
    try:
        answer = ask_with_llm(question, db, model=model)
        typer.echo(answer)
    except RuntimeError as e:
        typer.echo(str(e), err=True)
        raise typer.Exit(1) from e


def main() -> None:
    app()


if __name__ == "__main__":
    main()
