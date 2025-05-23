import asyncio
import contextlib
from random import randint
from threading import Event, Thread

import pytest

from picodi import ContextVarScope, Provide, SingletonScope, inject, registry


@pytest.mark.repeat(5)
def test_scope_resolving_races(start_race):
    @registry.set_scope(SingletonScope)
    def get_random_int():
        return randint(1, 10000)

    @inject
    def service(num: int = Provide(get_random_int)):
        return num

    results = []

    def actual_test():
        results.append(service())

    start_race(threads_num=8, target=actual_test)

    assert len(set(results)) == 1, results


@pytest.mark.repeat(5)
def test_scope_resolving_races_async(start_race):
    @registry.set_scope(SingletonScope)
    async def get_random_int():
        return randint(1, 10000)

    @inject
    async def service(num: int = Provide(get_random_int)):
        return num

    results = []

    async def main():
        results.append(await service())

    def actual_test():
        asyncio.run(main())

    start_race(threads_num=8, target=actual_test)

    assert len(set(results)) == 1, results


def test_contextvar_enter_is_thread_safe():
    scope = ContextVarScope()
    state = []
    numbers = iter(range(1000))
    event = Event()

    @contextlib.contextmanager
    def cm():
        number = next(numbers)
        state.append(f"open {number}")
        yield number
        state.append(f"close {number}")

    class TestThread(Thread):
        def run(self):
            event.wait(timeout=10)
            scope.enter(cm())
            scope.shutdown()

    threads = [TestThread() for _ in range(8)]
    for thread in threads:
        thread.start()

    event.set()

    for thread in threads:
        thread.join()

    assert state == [
        "open 0",
        "close 0",
        "open 1",
        "close 1",
        "open 2",
        "close 2",
        "open 3",
        "close 3",
        "open 4",
        "close 4",
        "open 5",
        "close 5",
        "open 6",
        "close 6",
        "open 7",
        "close 7",
    ]
