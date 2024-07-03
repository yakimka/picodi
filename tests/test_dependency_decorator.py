from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from picodi import (
    AutoScope,
    Provide,
    SingletonScope,
    dependency,
    init_dependencies,
    inject,
)

if TYPE_CHECKING:
    from collections.abc import Hashable


class IntMultiplierScope(AutoScope):
    def __init__(self) -> None:
        super().__init__()
        self._store: dict[Hashable, Any] = {}

    def get(self, key: Hashable) -> Any:
        result = self._store[key]
        return result * 2

    def set(self, key: Hashable, value: Any) -> None:
        self._store[key] = value * 2


def test_can_add_user_defined_scope():
    @dependency(scope_class=IntMultiplierScope)
    def get_num():
        return 42

    @inject
    def service(num: int = Provide(get_num)) -> int:
        return num

    # first call for storing value in scope
    # second call will get cached in scope value
    service()

    result = service()

    assert result == 42 * 2 * 2


async def test_can_add_user_defined_scope_async():
    @dependency(scope_class=IntMultiplierScope)
    async def get_num():
        return 42

    @inject
    async def service(num: int = Provide(get_num)) -> int:
        return num

    # first call for storing value in scope
    # second call will get cached in scope value
    await service()

    result = await service()

    assert result == 42 * 2 * 2


@pytest.fixture()
def tagged_dependencies():
    init_state = {
        "dep1": False,
        "dep2": False,
        "dep3": False,
    }

    @dependency(scope_class=SingletonScope, tags=["dep1", "group1"])
    def get_dep1():
        init_state["dep1"] = True
        yield 42

    @dependency(scope_class=SingletonScope, tags=["dep2", "group1"])
    def get_dep2():
        init_state["dep2"] = True
        yield 42

    @dependency(scope_class=SingletonScope, tags=["dep3", "group2"])
    def get_dep3():
        init_state["dep3"] = True
        yield 42

    return init_state


@pytest.fixture()
def tagged_dependencies_async():
    init_state = {
        "dep1": False,
        "dep2": False,
        "dep3": False,
    }

    @dependency(scope_class=SingletonScope, tags=["dep1", "group1"])
    async def get_dep1():
        init_state["dep1"] = True
        yield 42

    @dependency(scope_class=SingletonScope, tags=["dep2", "group1"])
    async def get_dep2():
        init_state["dep2"] = True
        yield 42

    @dependency(scope_class=SingletonScope, tags=["dep3", "group2"])
    async def get_dep3():
        init_state["dep3"] = True
        yield 42

    return init_state


tags_cases = [
    pytest.param(
        [],
        {"dep1": True, "dep2": True, "dep3": True},
        id="If no tags - init all",
    ),
    pytest.param(
        ["dep1"],
        {"dep1": True, "dep2": False, "dep3": False},
        id="Select one tag",
    ),
    pytest.param(
        ["dep1", "dep2"],
        {"dep1": True, "dep2": True, "dep3": False},
        id="Select multiple tags",
    ),
    pytest.param(
        ["group1"],
        {"dep1": True, "dep2": True, "dep3": False},
        id="Select deps that marked with same tag",
    ),
    pytest.param(
        ["dep1", "dep2", "dep3"],
        {"dep1": True, "dep2": True, "dep3": True},
        id="Select all tags",
    ),
    pytest.param(
        ["group1", "group2"],
        {"dep1": True, "dep2": True, "dep3": True},
        id="Select all tags (by groups)",
    ),
    pytest.param(
        ["group1", "-dep1"],
        {"dep1": False, "dep2": True, "dep3": False},
        id="Select group and exclude from this group",
    ),
    pytest.param(
        ["-dep1", "-dep2", "-dep3"],
        {"dep1": False, "dep2": False, "dep3": False},
        id="Deselect all deps",
    ),
    pytest.param(
        ["-group1", "-group2"],
        {"dep1": False, "dep2": False, "dep3": False},
        id="Deselect all deps (by groups)",
    ),
    pytest.param(
        ["-dep2"], {"dep1": True, "dep2": False, "dep3": True}, id="Init all except one"
    ),
]


@pytest.mark.parametrize("tags,expected_state", tags_cases)
def test_can_init_dependencies_by_selecting_tags(
    tags, expected_state, tagged_dependencies
):
    init_dependencies(tags=tags)

    assert tagged_dependencies == expected_state


@pytest.mark.parametrize("tags,expected_state", tags_cases)
async def test_can_init_dependencies_by_selecting_tags_async(
    tags, expected_state, tagged_dependencies_async
):
    await init_dependencies(tags=tags)

    assert tagged_dependencies_async == expected_state
