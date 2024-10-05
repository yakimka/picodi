from __future__ import annotations

from contextlib import ExitStack
from typing import TYPE_CHECKING

import pytest

from picodi import registry, shutdown_dependencies

if TYPE_CHECKING:
    from collections.abc import Callable, Generator


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "picodi_override(dep, override): Picodi deps override"
    )


@pytest.fixture()
def _picodi_shutdown() -> Generator[None, None, None]:
    """
    Shutdown dependencies after the test.
    Need for tests consistency.
    """
    yield
    shutdown_dependencies()


@pytest.fixture()
def _picodi_clear_touched() -> Generator[None, None, None]:
    """
    Clear touched dependencies after the test.
    Need for tests consistency.
    """
    yield
    registry.clear_touched()


@pytest.fixture(autouse=True)
def _picodi_teardown(_picodi_clear_touched: None, _picodi_shutdown: None) -> None:
    """
    Automatically cleanup Picodi dependencies and registry after the test.
    """


@pytest.fixture()
def picodi_overrides(request: pytest.FixtureRequest) -> list[tuple[Callable, Callable]]:
    """
    Get overrides from markers that will be used in the test.

    Usually, you don't need to use this fixture directly.
    Use `picodi_override` marker instead. But if you want to stick to
    some custom logic you can inherit from this fixture.
    """
    for marker in request.node.iter_markers(name="picodi_override"):
        if len(marker.args) not in (1, 2):
            pytest.fail(
                "picodi_override marker must have 2 arguments: dependency and override "
                "OR 1 argument: iterable of tuples with dependency and override"
            )

        overrides: list[tuple[Callable, Callable]] = (
            marker.args[0] if len(marker.args) == 1 else [marker.args]
        )
        if not isinstance(overrides, (list, tuple)):
            pytest.fail("Overrides must be a list or tuple")
        for dep, override in overrides:
            if not callable(dep) or not callable(override):
                pytest.fail("Dependency and override must be callable")

        return overrides
    return []


@pytest.fixture(autouse=True)
def _picodi_override_setup(
    picodi_overrides: list[tuple[Callable, Callable]],
) -> Generator[None, None, None]:
    with ExitStack() as stack:
        for get_dep, override in picodi_overrides:
            stack.enter_context(registry.override(get_dep, override))
        yield
