import inspect
import random

import pytest

from picodi import Provide, SingletonScope, dependency, init_dependencies, inject


def get_random_int():
    return random.randint(1, 100_000)


async def get_random_int_async():
    return random.randint(1, 100_000)


@pytest.fixture()
def get_redis_string_dep():
    @inject
    def get_redis_string(port: int = Provide(get_random_int)):
        return f"http://redis:{port}"

    return get_redis_string


@pytest.fixture()
def get_redis_string_async_dep():
    @inject
    async def get_redis_string_async(port: int = Provide(get_random_int_async)):
        return f"http://redis:{port}"

    return get_redis_string_async


@pytest.fixture()
def get_sync_dependency_in_async_context_dep():
    @inject
    async def get_sync_dependency_in_async_context(port: int = Provide(get_random_int)):
        return f"http://redis:{port}"

    return get_sync_dependency_in_async_context


def test_resolve_sync_dependency(get_redis_string_dep):
    result = get_redis_string_dep()

    _check_redis_string(result)


async def test_resolve_async_dependency(get_redis_string_async_dep):
    result = await get_redis_string_async_dep()

    _check_redis_string(result)


async def test_resolve_sync_dependency_in_async_function(
    get_sync_dependency_in_async_context_dep,
):
    result = await get_sync_dependency_in_async_context_dep()

    _check_redis_string(result)


def test_resolve_dependency_multiple_times_return_different_results(
    get_redis_string_dep,
):
    results = [get_redis_string_dep() for _ in range(30)]

    assert len(set(results)) > 1
    _check_redis_string(results[0])


@pytest.mark.parametrize(
    "func_name",
    ["get_redis_string_async_dep", "get_sync_dependency_in_async_context_dep"],
)
async def test_resolve_async_dependency_multiple_times_return_different_results(
    func_name,
    get_redis_string_async_dep,  # noqa: U100
    get_sync_dependency_in_async_context_dep,  # noqa: U100
):
    func = locals()[func_name]
    results = [await func() for _ in range(30)]

    assert len(set(results)) > 1
    _check_redis_string(results[0])


async def test_resolve_async_dependency_from_sync_function_return_coroutine():
    @inject
    def get_async_dep(port: int = Provide(get_random_int_async)):
        return port

    result = get_async_dep()

    assert inspect.iscoroutine(result)
    assert result.__name__ == "get_random_int_async"
    assert isinstance(await result, int)


def test_can_pass_dependency(get_redis_string_dep):
    result = get_redis_string_dep(port=100_000_000)

    assert result == "http://redis:100000000"


async def test_can_pass_dependency_async(get_redis_string_async_dep):
    result = await get_redis_string_async_dep(port=100_000_000)

    assert result == "http://redis:100000000"


def _check_redis_string(redis_string):
    __tracebackhide__ = True

    assert redis_string.startswith("http://redis:")
    assert int(redis_string.split(":")[-1]) <= 100_000


async def test_resolve_async_singleton_dependency_through_sync():
    @dependency(scope_class=SingletonScope, use_init_hook=True)
    async def get_client():
        return "my_client"

    @inject
    def get_client_sync(client: str = Provide(get_client)):
        return client

    @inject
    async def view(client: str = Provide(get_client_sync)):
        return client

    await init_dependencies([get_client])

    result = await view()

    assert result == "my_client"
