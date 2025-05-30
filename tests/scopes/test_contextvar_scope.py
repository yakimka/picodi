import asyncio

import pytest

from picodi import ContextVarScope, Provide, inject, registry


@pytest.fixture()
def sut():
    return ContextVarScope()


def test_can_store_and_then_get_value(sut):
    sut.set("key", "value", global_key=test_can_store_and_then_get_value)

    assert sut.get("key", global_key=test_can_store_and_then_get_value) == "value"


def test_store_cleared_after_shutdown(sut):
    sut.set("key", "value", global_key=test_store_cleared_after_shutdown)
    sut.shutdown(global_key=test_store_cleared_after_shutdown)

    with pytest.raises(KeyError):
        sut.get("key", global_key=test_store_cleared_after_shutdown)


def test_can_use_store_again_after_shutdown(sut):
    sut.set("key", "value", global_key=test_can_use_store_again_after_shutdown)
    sut.shutdown(global_key=test_can_use_store_again_after_shutdown)

    sut.set("key", "value", global_key=test_can_use_store_again_after_shutdown)
    assert sut.get("key", global_key=test_can_use_store_again_after_shutdown) == "value"


async def test_values_cant_be_retrieved_from_separate_task(sut):
    value_set = asyncio.Event()

    async def task1():
        sut.set(
            "key", "value1", global_key=test_values_cant_be_retrieved_from_separate_task
        )
        value_set.set()

    async def task2():
        await value_set.wait()
        with pytest.raises(KeyError):
            sut.get("key", global_key=test_values_cant_be_retrieved_from_separate_task)

    await asyncio.gather(task1(), task2())


async def test_shutdown_from_one_task_dont_affect_another_task(sut):
    value_set = asyncio.Event()
    scope_shutdown = asyncio.Event()

    async def task1():
        sut.set(
            "key",
            "value1",
            global_key=test_shutdown_from_one_task_dont_affect_another_task,
        )
        value_set.set()
        await scope_shutdown.wait()
        assert (
            sut.get(
                "key", global_key=test_shutdown_from_one_task_dont_affect_another_task
            )
            == "value1"
        )

    async def task2():
        await value_set.wait()
        sut.shutdown(global_key=test_shutdown_from_one_task_dont_affect_another_task)
        scope_shutdown.set()

    await asyncio.gather(task1(), task2())


async def test_closing_dependencies_in_one_task_dont_affect_another(make_closeable):
    closeables = [make_closeable() for _ in range(2)]
    closeable_gen = iter(closeables)
    first_shutdown = asyncio.Event()
    lock = asyncio.Lock()

    @registry.set_scope(ContextVarScope)
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

    async def manager1(closeable):
        await task1()
        assert closeable.is_closed is False
        async with lock:
            await registry.shutdown(scope_class=ContextVarScope)
            first_shutdown.set()

    async def manager2(closeable):
        async with lock:
            await task2()
            await first_shutdown.wait()
        assert closeable.is_closed is False
        await registry.shutdown(scope_class=ContextVarScope)

    closeable_task1, closeable_task2 = closeables
    await asyncio.gather(
        asyncio.create_task(manager1(closeable_task1)),
        asyncio.create_task(manager2(closeable_task2)),
    )

    assert closeable_task1.close_call_count == 1
    assert closeable_task2.close_call_count == 1
