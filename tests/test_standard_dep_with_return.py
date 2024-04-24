import inspect
import random

import pytest

from picodi import Provide, inject


def get_random_int():
    return random.randint(1, 100_000)


async def get_random_int_async():
    return random.randint(1, 100_000)


@inject
def get_redis_string(port: int = Provide(get_random_int)):
    return f"http://redis:{port}"


@inject
async def get_redis_string_async(port: int = Provide(get_random_int_async)):
    return f"http://redis:{port}"


@inject
async def get_redis_string_async_with_sync_dep(port: int = Provide(get_random_int)):
    return f"http://redis:{port}"


def test_resolve_sync_dependency():
    result = get_redis_string()

    _check_redis_string(result)


async def test_resolve_async_dependency():
    result = await get_redis_string_async()

    _check_redis_string(result)


async def test_resolve_sync_dependency_in_async_function():
    result = await get_redis_string_async_with_sync_dep()

    _check_redis_string(result)


def test_resolve_dependency_multiple_times_return_different_results():
    results = [get_redis_string() for _ in range(30)]

    assert len(set(results)) > 1
    _check_redis_string(results[0])


@pytest.mark.parametrize(
    "func", [get_redis_string_async, get_redis_string_async_with_sync_dep]
)
async def test_resolve_async_dependency_multiple_times_return_different_results(func):
    results = [await func() for _ in range(30)]

    assert len(set(results)) > 1
    _check_redis_string(results[0])


def test_resolve_async_dependency_from_sync_function_return_coroutine():
    @inject
    def get_async_dep(port: int = Provide(get_random_int_async)):
        return port

    result = get_async_dep()

    assert inspect.iscoroutine(result)
    assert result.__name__ == "get_random_int_async"


def test_can_pass_dependency():
    result = get_redis_string(port=100_000_000)

    assert result == "http://redis:100000000"


async def test_can_pass_dependency_async():
    result = await get_redis_string_async(port=100_000_000)

    assert result == "http://redis:100000000"


def _check_redis_string(redis_string):
    __tracebackhide__ = True

    assert redis_string.startswith("http://redis:")
    assert int(redis_string.split(":")[-1]) <= 100_000
