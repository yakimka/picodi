import asyncio
from random import randint

import pytest

from picodi import Provide, SingletonScope, inject, registry


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
