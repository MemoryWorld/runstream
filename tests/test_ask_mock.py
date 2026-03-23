from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from runstream.ingest import ingest_path


@pytest.fixture
def db_with_fixture(tmp_path: Path) -> Path:
    db = tmp_path / "ask.db"
    ingest_path(Path("fixtures/example_run"), db)
    return db


@patch("openai.OpenAI")
def test_ask_llm_tool_round_then_answer(
    mock_openai: MagicMock, db_with_fixture: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Regression: model calls search_runs, then returns text citing run_id."""
    monkeypatch.setenv("OPENAI_API_KEY", "fake-key")
    from runstream.ask import ask_with_llm

    tc = MagicMock()
    tc.id = "call_abc"
    tc.function.name = "search_runs"
    tc.function.arguments = '{"tag": "onnx-exported", "limit": 5}'

    msg1 = MagicMock()
    msg1.content = None
    msg1.tool_calls = [tc]

    choice1 = MagicMock()
    choice1.finish_reason = "tool_calls"
    choice1.message = msg1
    comp1 = MagicMock()
    comp1.choices = [choice1]

    msg2 = MagicMock()
    msg2.content = "The matching run_id is exp-2026-03-23-a7f3."
    msg2.tool_calls = None

    choice2 = MagicMock()
    choice2.finish_reason = "stop"
    choice2.message = msg2
    comp2 = MagicMock()
    comp2.choices = [choice2]

    client_inst = MagicMock()
    client_inst.chat.completions.create.side_effect = [comp1, comp2]
    mock_openai.return_value = client_inst

    out = ask_with_llm("Which run has tag onnx-exported?", db_with_fixture, model="gpt-4o-mini")
    assert "exp-2026-03-23-a7f3" in out
    assert client_inst.chat.completions.create.call_count == 2
