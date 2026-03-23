from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Iterator

from pydantic import ValidationError

from .models import RunRecord
from .store import connect, upsert_run


def iter_meta_files(root: Path) -> Iterator[Path]:
    root = root.resolve()
    if root.is_file():
        if root.name == "meta.json":
            yield root
        return
    yield from root.rglob("meta.json")


def load_record(path: Path) -> RunRecord:
    raw = path.read_bytes()
    data = json.loads(raw.decode("utf-8"))
    return RunRecord.model_validate(data)


def ingest_path(root: Path, db_path: Path) -> dict[str, int]:
    conn = connect(db_path)
    counts = {"inserted": 0, "updated": 0, "unchanged": 0, "errors": 0}
    for meta in iter_meta_files(root):
        try:
            record = load_record(meta)
            raw_hash = hashlib.sha256(record.canonical_json_bytes()).hexdigest()
            action = upsert_run(conn, record, str(meta.resolve()), raw_hash)
            counts[action] += 1
        except (json.JSONDecodeError, ValidationError, OSError):
            counts["errors"] += 1
    conn.close()
    return counts
