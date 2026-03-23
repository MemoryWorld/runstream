from __future__ import annotations

import json
from pathlib import Path

import pytest

from runstream.ingest import ingest_path
from runstream.tools import execute_tool, openai_tools_json


@pytest.fixture
def db_with_fixture(tmp_path: Path) -> Path:
    db = tmp_path / "t.db"
    ingest_path(Path("fixtures/example_run"), db)
    return db


def test_openai_tools_json_valid() -> None:
    raw = openai_tools_json()
    data = json.loads(raw)
    assert len(data) == 2
    names = {t["function"]["name"] for t in data}
    assert names == {"search_runs", "get_run"}


@pytest.mark.parametrize("case", json.loads(Path("fixtures/regression_tools.json").read_text()))
def test_execute_tool_regression(case: dict, db_with_fixture: Path) -> None:
    out = execute_tool(case["tool"], case["arguments"], db_with_fixture)
    assert case["expect_substring"] in out


def test_execute_tool_unknown_raises(db_with_fixture: Path) -> None:
    with pytest.raises(ValueError, match="unknown tool"):
        execute_tool("exec_shell", {}, db_with_fixture)
