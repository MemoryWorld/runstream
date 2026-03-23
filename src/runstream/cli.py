from __future__ import annotations

from pathlib import Path

import typer
import uvicorn

from .ingest import ingest_path

app = typer.Typer(no_args_is_help=True, add_completion=False)


@app.command("ingest-once")
def ingest_once(
    path: Path = typer.Argument(..., exists=True, help="File or directory to scan for meta.json"),
    db: Path = typer.Option(Path("runstream.db"), "--db", help="SQLite database path"),
) -> None:
    """Scan for meta.json files and upsert into SQLite."""
    stats = ingest_path(path, db)
    typer.echo(f"ingest complete -> {db}: {stats}")


@app.command("serve")
def serve(
    db: Path = typer.Option(Path("runstream.db"), "--db", help="SQLite database path"),
    host: str = typer.Option("127.0.0.1", "--host"),
    port: int = typer.Option(8000, "--port"),
) -> None:
    """Run HTTP API (FastAPI + uvicorn)."""
    import os

    os.environ["RUNSTREAM_DB"] = str(db.resolve())
    uvicorn.run(
        "runstream.api:app",
        host=host,
        port=port,
        factory=False,
    )


def main() -> None:
    app()


if __name__ == "__main__":
    main()
