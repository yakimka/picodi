from __future__ import annotations

from contextlib import nullcontext
from typing import TYPE_CHECKING, Any

import pytest

from picodi import AutoScope, ManualScope, Provide, inject, registry

if TYPE_CHECKING:
    from collections.abc import Hashable


@pytest.fixture()
def manual_scope():
    class MyManualScope(ManualScope):
        pass

    return MyManualScope()


class IntMultiplierScope(AutoScope):
    def __init__(self) -> None:
        super().__init__()
        self._store: dict[Hashable, Any] = {}

    def get(self, key: Hashable) -> Any:
        result = self._store[key]
        return result * 2

    def set(self, key: Hashable, value: Any) -> None:
        self._store[key] = value * 2


async def test_manual_scope_enter_shutdown(manual_scope):
    assert await manual_scope.enter(nullcontext()) is None
    assert await manual_scope.shutdown() is None


def test_can_add_user_defined_scope():
    @registry.set_scope(IntMultiplierScope)
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
    @registry.set_scope(IntMultiplierScope)
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
