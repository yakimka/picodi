import asyncio

import pytest

from picodi import ContextVarScope, Provide, dependency, inject, shutdown_dependencies


@pytest.fixture()
def sut():
    return ContextVarScope()


def test_can_store_and_then_get_value(sut):
    sut.set("key", "value")

    assert sut.get("key") == "value"


def test_store_cleared_after_shutdown(sut):
    sut.set("key", "value")
    sut.shutdown()

    with pytest.raises(KeyError):
        sut.get("key")


def test_can_use_store_again_after_shutdown(sut):
    sut.set("key", "value")
    sut.shutdown()

    sut.set("key", "value")
    assert sut.get("key") == "value"


async def test_values_cant_be_retrieved_from_separate_task(sut):
    value_set = asyncio.Event()

    async def task1():
        sut.set("key", "value1")
        value_set.set()

    async def task2():
        await value_set.wait()
        with pytest.raises(KeyError):
            sut.get("key")

    await asyncio.gather(task1(), task2())


async def test_shutdown_from_one_task_dont_affect_another_task(sut):
    value_set = asyncio.Event()
    scope_shutdown = asyncio.Event()

    async def task1():
        sut.set("key", "value1")
        value_set.set()
        await scope_shutdown.wait()
        assert sut.get("key") == "value1"

    async def task2():
        await value_set.wait()
        sut.shutdown()
        scope_shutdown.set()

    await asyncio.gather(task1(), task2())


async def test_closing_dependencies_in_one_task_dont_affect_another(make_closeable):
    closeables = [make_closeable() for _ in range(2)]
    closeable_gen = iter(closeables)

    @dependency(scope_class=ContextVarScope)
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
