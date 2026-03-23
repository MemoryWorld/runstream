import pytest

from runstream.http_middleware import clear_rate_limit_state_for_tests


@pytest.fixture(autouse=True)
def _clear_rate_limit_between_tests() -> None:
    clear_rate_limit_state_for_tests()
    yield
    clear_rate_limit_state_for_tests()
