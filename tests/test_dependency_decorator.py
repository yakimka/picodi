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


def test_can_optionally_set_manual_initialization():
    # Arrange
    inited = False

    @dependency(scope_class=SingletonScope, use_init_hook=True)
    def get_num():
        nonlocal inited
        inited = True
        yield 42

    # Act
    init_dependencies()

    # Assert
    assert inited is True


async def test_can_optionally_set_manual_initialization_async():
    # Arrange
    inited = False

    @dependency(scope_class=SingletonScope, use_init_hook=True)
    async def get_num():
        nonlocal inited
        inited = True
        yield 42

    # Act
    await init_dependencies()

    # Assert
    assert inited is True


def test_can_optionally_set_manual_initialization_with_callable():
    # Arrange
    inited = False

    @inject
    def callable_func(flag: bool = Provide(lambda: True)):
        return flag

    @dependency(scope_class=SingletonScope, use_init_hook=callable_func)
    def get_num():
        nonlocal inited
        inited = True
        yield 42

    # Act
    init_dependencies()

    # Assert
    assert inited is True


async def test_can_optionally_set_manual_initialization_with_callable_async():
    # Arrange
    inited = False

    @inject
    def callable_func(flag: bool = Provide(lambda: True)):
        return flag

    @dependency(scope_class=SingletonScope, use_init_hook=callable_func)
    async def get_num():
        nonlocal inited
        inited = True
        yield 42

    # Act
    await init_dependencies()

    # Assert
    assert inited is True
