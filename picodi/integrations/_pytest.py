from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from picodi import Context

if TYPE_CHECKING:
    from collections.abc import Generator


@pytest.fixture()
def picodi_context() -> Context | list[Context]:
    """
    Fixture to provide a context for the test.
    """
    return []


@pytest.fixture()
def _ensure_context_list(
    picodi_context: Context | list[Context],
) -> list[Context]:
    return [picodi_context] if isinstance(picodi_context, Context) else picodi_context


@pytest.fixture()
def _picodi_clear_touched(_ensure_context_list) -> Generator[None, None, None]:
    """
    Clear touched dependencies after the test.
    Need for tests consistency.
    """
    yield
    for context in _ensure_context_list:
        context.clear_touched()


@pytest.fixture(autouse=True)
def _pytest_autouse_fixture(
    _picodi_clear_touched: None,
) -> None:
    """
    Just a fixture to make sure that all the autouse fixtures are used.
    """
