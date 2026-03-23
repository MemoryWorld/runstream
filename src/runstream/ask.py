from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .tools import OPENAI_TOOLS, execute_tool

MAX_TOOL_ROUNDS = 8


def _assistant_message_dict(msg: Any) -> dict[str, Any]:
    """Convert OpenAI SDK assistant message to API-shaped dict."""
    d: dict[str, Any] = {"role": "assistant", "content": msg.content}
    if getattr(msg, "tool_calls", None):
        d["tool_calls"] = [
            {
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            }
            for tc in msg.tool_calls
        ]
    return d


def ask_with_llm(question: str, db_path: Path, *, model: str | None = None) -> str:
    """
    Optional LLM: requires OPENAI_API_KEY and pip install 'runstream[llm]'.
    Only tools: search_runs, get_run (see tools.py). No shell.
    """
    try:
        from openai import OpenAI
    except ImportError as e:
        raise RuntimeError(
            "Install LLM extra: pip install 'runstream[llm]'"
        ) from e

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Set OPENAI_API_KEY to use ask_with_llm")

    base_url = os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1")
    model_name = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    client = OpenAI(api_key=api_key, base_url=base_url)
    messages: list[dict[str, Any]] = [{"role": "user", "content": question}]

    for _ in range(MAX_TOOL_ROUNDS):
        completion = client.chat.completions.create(
            model=model_name,
            messages=messages,
            tools=OPENAI_TOOLS,
            tool_choice="auto",
        )
        choice = completion.choices[0]
        msg = choice.message

        if choice.finish_reason == "tool_calls" and msg.tool_calls:
            messages.append(_assistant_message_dict(msg))
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                result = execute_tool(tc.function.name, args, db_path)
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tc.id,
                        "content": result,
                    }
                )
            continue

        return (msg.content or "").strip()

    return ""
