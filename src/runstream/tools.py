from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .store import connect, get_run, list_runs

# OpenAI Chat Completions "tools" format (function calling)
OPENAI_TOOLS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "search_runs",
            "description": (
                "Search the experiment run catalog. Returns items and total count. "
                "Use filters to narrow by project, tag, or minimum started_at (ISO-8601)."
            ),
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Max rows (1-200)",
                        "default": 20,
                    },
                    "offset": {"type": "integer", "default": 0},
                    "project": {"type": "string", "description": "Exact project name"},
                    "tag": {"type": "string", "description": "Tag must be present on the run"},
                    "since": {
                        "type": "string",
                        "description": "Only runs with started_at >= this ISO-8601 timestamp",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_run",
            "description": "Fetch a single run by run_id, including metrics and artifacts.",
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "required": ["run_id"],
                "properties": {
                    "run_id": {"type": "string", "description": "Unique run identifier"},
                },
            },
        },
    },
]


def execute_tool(name: str, arguments: dict[str, Any], db_path: Path) -> str:
    """
    Dispatch tool calls. Returns JSON string for the model (no shell, no arbitrary code).
    Unknown tools raise ValueError.
    """
    conn = connect(db_path)
    try:
        if name == "search_runs":
            limit = min(200, max(1, int(arguments.get("limit", 20))))
            offset = max(0, int(arguments.get("offset", 0)))
            result = list_runs(
                conn,
                limit=limit,
                offset=offset,
                project=arguments.get("project"),
                tag=arguments.get("tag"),
                since=arguments.get("since"),
            )
            return json.dumps({"items": result.items, "total": result.total}, default=str)
        if name == "get_run":
            run_id = arguments.get("run_id")
            if not run_id:
                return json.dumps({"error": "run_id required"})
            row = get_run(conn, str(run_id))
            return json.dumps(row if row else {"error": "not found"}, default=str)
        raise ValueError(f"unknown tool: {name}")
    finally:
        conn.close()


def openai_tools_json() -> str:
    return json.dumps(OPENAI_TOOLS, indent=2)
