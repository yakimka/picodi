import asyncio

import pytest

from picodi import NullScope, Provide, dependency, inject


@pytest.fixture()
def sut():
    return NullScope()


def test_scope_not_store_anything(sut):
    sut.set("key", "value")

    with pytest.raises(KeyError):
        sut.get("key")


async def test_closing_one_dependency_dont_affect_another(make_closeable):
    closeables = [make_closeable() for _ in range(2)]
    closeable_gen = iter(closeables)
    closeable_task1, closeable_task2 = closeables
    first_dep_enter = asyncio.Event()
    second_dep_enter = asyncio.Event()
    first_dep_close = asyncio.Event()

    @dependency(scope_class=NullScope)
    async def dummy_dep():
        closeable = next(closeable_gen)
        yield closeable
        closeable.close()

    @inject
    async def task1(dep: str = Provide(dummy_dep)):  # noqa: U100
        first_dep_enter.set()
        await second_dep_enter.wait()
        return None

    @inject
    async def task2(dep: str = Provide(dummy_dep)):  # noqa: U100
        await first_dep_enter.wait()
        second_dep_enter.set()
        await first_dep_close.wait()
        assert closeable_task1.is_closed is True
        assert closeable_task2.is_closed is False
        return None

    async def manager1(closeable):
        assert closeable.is_closed is False
        await task1()
        assert closeable.is_closed is True
        first_dep_close.set()  # type: ignore[unreachable]

    async def manager2(closeable):
        assert closeable.is_closed is False
        await task2()
        assert closeable.is_closed is True

    await asyncio.gather(
        asyncio.create_task(manager1(closeable_task1)),
        asyncio.create_task(manager2(closeable_task2)),
    )

    assert closeable_task1.close_call_count == 1
    assert closeable_task2.close_call_count == 1
