import asyncio

import pytest

from picodi import NullScope, Provide, dependency, inject, shutdown_dependencies


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

    @dependency(scope_class=NullScope)
    async def dummy_dep():
        closeable = next(closeable_gen)
        yield closeable
        closeable.close()

    @inject
    async def task1(dep: str = Provide(dummy_dep)):  # noqa: U100
        return None

    @inject
    async def task2(dep: str = Provide(dummy_dep)):  # noqa: U100
        return None

    async def manager(task, closeable, sleep: float = 0):
        await task
        await asyncio.sleep(sleep)
        assert closeable.is_closed is False
        await shutdown_dependencies()

    closeable_task1, closeable_task2 = closeables
    await asyncio.gather(
        manager(task1(), closeable_task1), manager(task2(), closeable_task2, 0.2)
    )

    assert closeable_task1.close_call_count == 1
    assert closeable_task2.close_call_count == 1
