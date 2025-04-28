from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pytest

from picodi import NullScope, Provide, inject

if TYPE_CHECKING:
    from collections.abc import Hashable


@pytest.fixture()
def custom_scope():
    events = set()

    class CustomScope(NullScope):
        def get(self, key: Hashable) -> Any:
            events.add("get()")
            return super().get(key)

        def set(self, key: Hashable, value: Any) -> None:
            events.add(f"set({value})")
            super().set(key, value)

    return CustomScope, events


def test_dependency_uses_custom_scope(custom_scope, make_context):
    def get_num():
        return 42

    @inject
    def service(num: int = Provide(get_num)) -> int:
        return num

    custom_scope_class, events = custom_scope
    context = make_context((get_num, custom_scope_class))

    with context:
        result = service()

    assert result == 42
    assert events == {"get()", "set(42)"}


async def test_dependency_uses_custom_scope_async(custom_scope, make_context):
    async def get_num():
        return 42

    @inject
    async def service(num: int = Provide(get_num)) -> int:
        return num

    custom_scope_class, events = custom_scope
    context = make_context((get_num, custom_scope_class))

    async with context:
        result = await service()

    assert result == 42
    assert events == {"get()", "set(42)"}
