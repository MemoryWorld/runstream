from __future__ import annotations

import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from .ingest import ingest_path


class _DebouncedIngest:
    def __init__(self, root: Path, db: Path, debounce_sec: float) -> None:
        self.root = root.resolve()
        self.db = db.resolve()
        self.debounce_sec = debounce_sec
        self._timer: threading.Timer | None = None
        self._lock = threading.Lock()

    def bump(self) -> None:
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self.debounce_sec, self._run_ingest)
            self._timer.daemon = True
            self._timer.start()

    def _run_ingest(self) -> None:
        with self._lock:
            self._timer = None
        t0 = time.perf_counter()
        stats = ingest_path(self.root, self.db)
        dt = time.perf_counter() - t0
        print(f"[runstream-watch] ingest in {dt:.2f}s -> {stats}", flush=True)


class _MetaJsonHandler(FileSystemEventHandler):
    def __init__(self, debounced: _DebouncedIngest) -> None:
        self._d = debounced

    def _maybe_bump(self, path: str) -> None:
        if path.endswith("meta.json") or path.endswith("meta.json.tmp"):
            self._d.bump()

    def on_created(self, event):  # type: ignore[no-untyped-def]
        if event.is_directory:
            return
        self._maybe_bump(event.src_path)

    def on_modified(self, event):  # type: ignore[no-untyped-def]
        if event.is_directory:
            return
        self._maybe_bump(event.src_path)

    def on_moved(self, event):  # type: ignore[no-untyped-def]
        if not event.is_directory:
            self._maybe_bump(event.dest_path)


def watch_and_ingest(root: Path, db: Path, debounce_sec: float = 2.0) -> None:
    """Block until Ctrl+C: debounce re-ingest when meta.json changes under root."""
    debounced = _DebouncedIngest(root, db, debounce_sec)
    handler = _MetaJsonHandler(debounced)
    observer = Observer()
    watch_root = root.resolve()
    if watch_root.is_file():
        watch_root = watch_root.parent
    observer.schedule(handler, str(watch_root), recursive=True)
    observer.start()
    print(f"[runstream-watch] watching {watch_root} -> db {db.resolve()}", flush=True)
    debounced.bump()  # initial ingest
    try:
        while True:
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        observer.stop()
        observer.join(timeout=5)
