from __future__ import annotations

from typing import TYPE_CHECKING, Any

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
        if isinstance(result, int):
            return result * 2
        return result

    def set(self, key: Hashable, value: Any) -> None:
        if isinstance(value, int):
            value = value * 2
        self._store[key] = value


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


def test_can_optionally_ignore_manual_initialization():
    # Arrange
    inited = False

    @dependency(scope_class=SingletonScope, ignore_manual_init=True)
    def get_num():
        nonlocal inited
        inited = True
        yield 42

    @inject
    def service(num: int = Provide(get_num)) -> int:
        return num

    # Act
    init_dependencies()

    # Assert
    assert inited is False

    assert service() == 42
    assert inited is True


async def test_can_optionally_ignore_manual_initialization_async():
    # Arrange
    inited = False

    @dependency(scope_class=SingletonScope, ignore_manual_init=True)
    async def get_num():
        nonlocal inited
        inited = True
        yield 42

    @inject
    async def service(num: int = Provide(get_num)) -> int:
        return num

    # Act
    await init_dependencies()

    # Assert
    assert inited is False

    assert await service() == 42
    assert inited is True
