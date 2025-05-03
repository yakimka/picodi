import inspect
import random
from dataclasses import dataclass

import pytest

from picodi import NullScope, Provide, SingletonScope, inject, registry


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
    @registry.set_scope(scope_class=SingletonScope)
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
    @registry.set_scope(scope_class=SingletonScope)
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
    @registry.set_scope(scope_class=SingletonScope)
    async def async_singleton_scope_dep():
        int_service = IntService.create()
        yield int_service
        await int_service.aclose()

    @inject
    def get_async_dep(port: int = Provide(async_singleton_scope_dep)):
        return port

    await registry.init([async_singleton_scope_dep])
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
    @registry.set_scope(scope_class=SingletonScope)
    def async_singleton_scope_dep():
        int_service = IntService.create()
        yield int_service
        int_service.close()

    @inject
    def get_async_dep(port: int = Provide(async_singleton_scope_dep)):
        return port

    result = get_async_dep()
    assert result.closed is False

    registry.shutdown()

    assert result.closed is True


async def test_singleton_scope_dep_can_be_closed_manually_async():
    @registry.set_scope(scope_class=SingletonScope)
    async def async_singleton_scope_dep():
        int_service = IntService.create()
        yield int_service
        await int_service.aclose()

    @inject
    async def get_async_dep(port: int = Provide(async_singleton_scope_dep)):
        return port

    result = await get_async_dep()
    assert result.closed is False

    await registry.shutdown()

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

    @registry.set_scope(scope_class=SingletonScope)
    @inject
    def my_singleton_scope_dep(number: int = Provide(get_42)):
        assert number == 42
        nonlocal called
        called += 1
        return number

    registry.init([my_singleton_scope_dep])

    assert called == 1


async def test_can_init_injected_singleton_scope_dep_async():
    called = 0

    def get_42():
        return 42

    @registry.set_scope(scope_class=SingletonScope)
    @inject
    async def my_async_singleton_scope_dep(number: int = Provide(get_42)):
        assert number == 42
        nonlocal called
        called += 1
        return number

    await registry.init([my_async_singleton_scope_dep])

    assert called == 1


def test_can_init_injected_singleton_scope_dep_argument_passed_as_callable():
    called = 0

    def get_42():
        return 42

    @registry.set_scope(scope_class=SingletonScope)
    @inject
    def my_singleton_scope_dep(number: int = Provide(get_42)):
        assert number == 42
        nonlocal called
        called += 1
        return number

    registry.init(lambda: [my_singleton_scope_dep])

    assert called == 1


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


async def test_resources_are_closed_even_if_exception_raised():
    int_service = IntService.create()

    def get_int_service():
        try:
            yield int_service
        finally:
            int_service.close()

    @inject
    def get_int(service: IntService = Provide(get_int_service)) -> IntService:
        assert service.closed is False
        raise ValueError("Something went wrong")

    with pytest.raises(ValueError, match="Something went wrong"):
        get_int()

    assert int_service.closed is True


async def test_resources_are_closed_even_if_exception_raised_async():
    int_service = IntService.create()

    async def get_int_service():
        try:
            yield int_service
        finally:
            await int_service.aclose()

    @inject
    async def get_int(service: IntService = Provide(get_int_service)) -> IntService:
        assert service.closed is False
        raise ValueError("Something went wrong")

    with pytest.raises(ValueError, match="Something went wrong"):
        await get_int()

    assert int_service.closed is True


def test_resources_closed_after_generator_consumed(closeable):
    def get_yield_dep():
        yield closeable
        closeable.close()

    @inject
    def my_generator(dep=Provide(get_yield_dep)):
        yield from range(3)
        assert dep.is_closed is False

    result = list(my_generator())

    assert result == [0, 1, 2]
    assert closeable.is_closed is True


async def test_resources_closed_after_generator_consumed_async(closeable):
    async def get_yield_dep():
        yield closeable
        closeable.close()

    @inject
    async def my_generator(dep=Provide(get_yield_dep)):
        for i in range(3):
            yield i
        assert dep.is_closed is False

    result = [i async for i in my_generator()]

    assert result == [0, 1, 2]
    assert closeable.is_closed is True


@pytest.mark.parametrize("scope_class", [NullScope, SingletonScope])
async def test_resources_not_closed_without_finally_block(scope_class):
    int_service = IntService.create()

    @registry.set_scope(scope_class=scope_class)
    def get_int_service():
        yield int_service

    @inject
    def get_int(service: IntService = Provide(get_int_service)) -> IntService:
        assert service.closed is False
        raise ValueError("Something went wrong")

    with pytest.raises(ValueError, match="Something went wrong"):
        get_int()

    assert int_service.closed is False


@pytest.mark.parametrize("scope_class", [NullScope, SingletonScope])
async def test_resources_not_closed_without_finally_block_async(scope_class):
    int_service = IntService.create()

    @registry.set_scope(scope_class=scope_class)
    async def get_int_service():
        yield int_service

    @inject
    async def get_int(service: IntService = Provide(get_int_service)) -> IntService:
        assert service.closed is False
        raise ValueError("Something went wrong")

    with pytest.raises(ValueError, match="Something went wrong"):
        await get_int()

    assert int_service.closed is False
