import inspect
import random
from dataclasses import dataclass

import pytest

from picodi import (
    Provide,
    SingletonScope,
    dependency,
    init_dependencies,
    inject,
    shutdown_dependencies,
)


@dataclass
class IntService:
    value: int
    closed: bool = False

    @classmethod
    def create(cls):
        return cls(random.randint(1, 100_000))

    def close(self):
        self.closed = True

    async def aclose(self):
        self.closed = True


def get_int_service():
    int_service = IntService.create()
    yield int_service
    int_service.close()


@pytest.fixture()
def int_service_singleton_scope_dep():
    @dependency(scope_class=SingletonScope)
    def get_int_service_singleton_scope_dep():
        int_service = IntService.create()
        yield int_service
        int_service.close()

    return get_int_service_singleton_scope_dep


async def get_int_service_async():
    int_service = IntService.create()
    yield int_service
    await int_service.aclose()


@pytest.fixture()
def int_service_async_singleton_scope_dep():
    @dependency(scope_class=SingletonScope)
    async def get_int_service_async_singleton_scope_dep():
        int_service = IntService.create()
        yield int_service
        await int_service.aclose()

    return get_int_service_async_singleton_scope_dep


def test_resolve_yield_dep_sync():
    @inject
    def get_int(service: IntService = Provide(get_int_service)):
        assert service.closed is False
        return service

    int_service = get_int()
    assert isinstance(int_service, IntService)
    assert int_service.closed is True


def test_multiple_calls_to_yield_dep_sync_return_different_values():
    @inject
    def get_int(service: IntService = Provide(get_int_service)):
        return service

    int_service_1 = get_int()
    int_service_2 = get_int()

    assert isinstance(int_service_1, IntService)
    assert isinstance(int_service_2, IntService)
    assert int_service_1 is not int_service_2


async def test_resolve_yield_dep_async():
    @inject
    async def get_int(service: IntService = Provide(get_int_service_async)):
        assert service.closed is False
        return service

    int_service = await get_int()

    assert isinstance(int_service, IntService)
    assert int_service.closed is True


async def test_resolve_yield_dep_sync_from_async_context():
    @inject
    async def get_int(service: IntService = Provide(get_int_service)):
        assert service.closed is False
        return service

    int_service = await get_int()

    assert isinstance(int_service, IntService)
    assert int_service.closed is True


async def test_multiple_calls_to_yield_dep_async_return_different_values():
    @inject
    async def get_int(service: IntService = Provide(get_int_service_async)):
        return service

    int_service_1 = await get_int()
    int_service_2 = await get_int()

    assert isinstance(int_service_1, IntService)
    assert isinstance(int_service_2, IntService)
    assert int_service_1 is not int_service_2


def test_multiple_calls_to_singleton_scope_dep_sync_return_same_values(
    int_service_singleton_scope_dep,
):
    @inject
    def get_int(service: IntService = Provide(int_service_singleton_scope_dep)):
        return service

    int_service_1 = get_int()
    int_service_2 = get_int()

    assert isinstance(int_service_1, IntService)
    assert int_service_1 is int_service_2


async def test_multiple_calls_to_singleton_scope_dep_async_return_same_values(
    int_service_async_singleton_scope_dep,
):
    @inject
    async def get_int(
        service: IntService = Provide(int_service_async_singleton_scope_dep),
    ):
        return service

    int_service_1 = await get_int()
    int_service_2 = await get_int()

    assert isinstance(int_service_1, IntService)
    assert int_service_1 is int_service_2


async def test_multiple_calls_to_singleton_scope_dep_sync_from_async_context_same_val(
    int_service_singleton_scope_dep,
):
    @inject
    async def get_int(service: IntService = Provide(int_service_singleton_scope_dep)):
        return service

    int_service_1 = await get_int()
    int_service_2 = await get_int()

    assert isinstance(int_service_1, IntService)
    assert int_service_1 is int_service_2


def test_resolve_async_yield_dep_from_sync_function_return_coroutine():
    @inject
    def get_async_dep(port: int = Provide(get_int_service_async)):
        return port

    result = get_async_dep()

    assert inspect.isasyncgen(result)
    assert result.__name__ == "get_int_service_async"


async def test_resolve_async_yield_dep_from_sync_function_can_be_inited():
    @dependency(scope_class=SingletonScope)
    async def async_singleton_scope_dep():
        int_service = IntService.create()
        yield int_service
        await int_service.aclose()

    @inject
    def get_async_dep(port: int = Provide(async_singleton_scope_dep)):
        return port

    await init_dependencies()
    result = get_async_dep()

    assert isinstance(result, IntService)


def test_singleton_scope_dep_doesnt_close_automatically(
    int_service_singleton_scope_dep,
):
    @inject
    def get_int(service: IntService = Provide(int_service_singleton_scope_dep)):
        return service

    int_service = get_int()
    assert int_service.closed is False


async def test_singleton_scope_dep_doesnt_close_automatically_async(
    int_service_async_singleton_scope_dep,
):
    @inject
    async def get_int(
        service: IntService = Provide(int_service_async_singleton_scope_dep),
    ):
        return service

    int_service = await get_int()
    assert int_service.closed is False


async def test_singleton_scope_dep_doesnt_close_automatically_sync_from_async_context(
    int_service_singleton_scope_dep,
):
    @inject
    async def get_int(service: IntService = Provide(int_service_singleton_scope_dep)):
        return service

    int_service = await get_int()
    assert int_service.closed is False


def test_singleton_scope_dep_can_be_closed_manually():
    @dependency(scope_class=SingletonScope)
    def async_singleton_scope_dep():
        int_service = IntService.create()
        yield int_service
        int_service.close()

    @inject
    def get_async_dep(port: int = Provide(async_singleton_scope_dep)):
        return port

    result = get_async_dep()
    assert result.closed is False

    shutdown_dependencies()

    assert result.closed is True


async def test_singleton_scope_dep_can_be_closed_manually_async():
    @dependency(scope_class=SingletonScope)
    async def async_singleton_scope_dep():
        int_service = IntService.create()
        yield int_service
        await int_service.aclose()

    @inject
    async def get_async_dep(port: int = Provide(async_singleton_scope_dep)):
        return port

    result = await get_async_dep()
    assert result.closed is False

    await shutdown_dependencies()

    assert result.closed is True


async def test_can_resolve_injected_generator():
    @inject
    def get_int_service():
        int_service = IntService.create()
        yield int_service
        int_service.close()

    @inject
    def get_int(service: IntService = Provide(get_int_service)) -> IntService:
        return service

    result = get_int()

    assert isinstance(result, IntService)
    assert result.closed is True


async def test_can_resolve_injected_generator_async():
    @inject
    async def get_int_service():
        int_service = IntService.create()
        yield int_service
        await int_service.aclose()

    @inject
    async def get_int(service: IntService = Provide(get_int_service)) -> IntService:
        return service

    result = await get_int()

    assert isinstance(result, IntService)
    assert result.closed is True


async def test_can_resolve_sync_injected_generator_in_async_context():
    @inject
    def get_int_service():
        int_service = IntService.create()
        yield int_service
        int_service.close()

    @inject
    async def get_int(service: IntService = Provide(get_int_service)) -> IntService:
        return service

    result = await get_int()

    assert isinstance(result, IntService)
    assert result.closed is True


def test_can_init_injected_singleton_scope_dep():
    called = 0

    def get_42():
        return 42

    @dependency(scope_class=SingletonScope)
    @inject
    def my_singleton_scope_dep(number: int = Provide(get_42)):
        assert number == 42
        nonlocal called
        called += 1
        return number

    Provide(my_singleton_scope_dep)  # for registering dependency

    init_dependencies()

    assert called == 1


async def test_can_init_injected_singleton_scope_dep_async():
    called = 0

    def get_42():
        return 42

    @dependency(scope_class=SingletonScope)
    @inject
    async def my_async_singleton_scope_dep(number: int = Provide(get_42)):
        assert number == 42
        nonlocal called
        called += 1
        return number

    Provide(my_async_singleton_scope_dep)  # for registering dependency

    await init_dependencies()

    assert called == 1


async def test_dont_init_not_used_singleton_scope_deps():
    @dependency(scope_class=SingletonScope)
    async def not_used_singleton_scope_dep():
        yield 1 / 0  # pragma: no cover

    @dependency(scope_class=SingletonScope)
    async def used_singleton_scope_dep():
        yield 42

    @inject
    def get_async_dep(num: int = Provide(used_singleton_scope_dep)):
        return num

    await init_dependencies()
    result = get_async_dep()

    assert result == 42


async def test_can_resolve_yield_in_yield_with_correct_scopes():
    context_calls = []

    def get_a_dep():
        context_calls.append("get_a_dep")
        yield "a"
        context_calls.append("close_a_dep")

    @inject
    def get_b_dep(a: str = Provide(get_a_dep)):
        context_calls.append("get_b_dep")
        yield a, "b"
        context_calls.append("close_b_dep")

    @inject
    def service(b: tuple[str, str] = Provide(get_b_dep)):
        return b

    result = service()

    assert result == ("a", "b")
    assert context_calls == ["get_a_dep", "get_b_dep", "close_b_dep", "close_a_dep"]


async def test_can_resolve_yield_in_yield_with_correct_scopes_async():
    context_calls = []

    async def get_a_dep():
        context_calls.append("get_a_dep")
        yield "a"
        context_calls.append("close_a_dep")

    @inject
    async def get_b_dep(a: str = Provide(get_a_dep)):
        context_calls.append("get_b_dep")
        yield a, "b"
        context_calls.append("close_b_dep")

    @inject
    async def service(b: tuple[str, str] = Provide(get_b_dep)):
        return b

    result = await service()

    assert result == ("a", "b")
    assert context_calls == ["get_a_dep", "get_b_dep", "close_b_dep", "close_a_dep"]
