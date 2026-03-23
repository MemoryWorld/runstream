import pytest
from fastapi.testclient import TestClient

from runstream.api import app


@pytest.fixture
def client_rl(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setenv("RUNSTREAM_ENABLE_RATE_LIMIT", "1")
    monkeypatch.setenv("RUNSTREAM_RATE_LIMIT_RPM", "2")
    return TestClient(app)


def test_rate_limit_exempt_health(client_rl: TestClient) -> None:
    for _ in range(5):
        assert client_rl.get("/health").status_code == 200


def test_rate_limit_429_on_runs(client_rl: TestClient) -> None:
    assert client_rl.get("/runs").status_code == 200
    assert client_rl.get("/runs").status_code == 200
    r = client_rl.get("/runs")
    assert r.status_code == 429
    assert r.json().get("detail") == "rate limit exceeded"


def test_rate_limit_disabled_by_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("RUNSTREAM_ENABLE_RATE_LIMIT", raising=False)
    with TestClient(app) as c:
        for _ in range(5):
            assert c.get("/runs").status_code == 200
