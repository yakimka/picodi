from __future__ import annotations

from contextlib import ExitStack
from typing import TYPE_CHECKING

import pytest

from picodi import Registry
from picodi import registry as default_registry

if TYPE_CHECKING:
    from collections.abc import Callable, Generator


def pytest_configure(config: pytest.Config) -> None:
    config.addinivalue_line(
        "markers", "picodi_override(dep, override): Picodi deps override"
    )
    config.addinivalue_line(
        "markers",
        "picodi_init_dependencies(dependencies): Helper marker for initializing deps",
    )


@pytest.fixture()
def custom_registries() -> list[Registry]:
    """
    Fixture that returns a list of user-defined registries.
    This is useful for testing multiple registries at once.
    """
    return []


@pytest.fixture()
def registries(
    custom_registries: list[Registry],
) -> list[Registry]:
    """
    Fixture that returns the default registry and any user-defined registries.
    """
    items = list(custom_registries)
    if default_registry not in items:
        items.append(default_registry)
    return items


@pytest.fixture()
def _picodi_shutdown(registries: list[Registry]) -> Generator[None]:
    """
    Shutdown dependencies after the test.
    Need for tests consistency.
    """
    yield
    for registry in registries:
        registry.shutdown()


@pytest.fixture()
def _picodi_clear_touched(registries: list[Registry]) -> Generator[None]:
    """
    Clear touched dependencies after the test.
    Need for tests consistency.
    """
    yield
    for registry in registries:
        registry.clear_touched()


@pytest.fixture()
def picodi_overrides() -> list[tuple[Callable, Callable]]:
    """
    Get overrides from markers that will be used in the test.

    Usually, you don't need to use this fixture directly.
    Use `picodi_override` marker instead. But if you want to stick to
    some custom logic you can inherit from this fixture.
    """
    return []


@pytest.fixture()
def picodi_overrides_from_marks(
    request: pytest.FixtureRequest,
) -> list[tuple[Callable, Callable]]:
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


@pytest.fixture()
def _picodi_override_setup(
    picodi_overrides: list[tuple[Callable, Callable]],
    picodi_overrides_from_marks: list[tuple[Callable, Callable]],
    registries: list[Registry],
) -> Generator[None]:
    overrides = []
    for item in picodi_overrides_from_marks + picodi_overrides:
        if item not in overrides:
            overrides.append(item)
    with ExitStack() as stack:
        for get_dep, override in overrides:
            for registry in registries:
                stack.enter_context(registry.override(get_dep, override))
        yield


@pytest.fixture()
def picodi_init_dependencies_kwargs(request: pytest.FixtureRequest) -> dict | None:
    for marker in request.node.iter_markers(name="picodi_init_dependencies"):
        if marker.args:
            raise ValueError(
                "init_dependencies marker don't support positional arguments"
            )
        if not marker.kwargs:
            raise ValueError("init_dependencies marker must have keyword arguments")
        return marker.kwargs
    return None


@pytest.fixture()
def _picodi_init_dependencies(
    picodi_init_dependencies_kwargs: dict | None,
    registries: list[Registry],
) -> None:
    if picodi_init_dependencies_kwargs is None:
        return
    for registry in registries:
        registry.init(**picodi_init_dependencies_kwargs)


@pytest.fixture(autouse=True)
def _pytest_autouse_fixture(
    _picodi_override_setup: None,
    _picodi_init_dependencies: None,
    _picodi_clear_touched: None,
    _picodi_shutdown: None,
) -> None:
    """
    Just a fixture to make sure that all the autouse fixtures are used.
    """
