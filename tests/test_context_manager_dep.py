import inspect
import random
from dataclasses import dataclass

import pytest

from picodi import Provide, init_resources, inject, resource, shutdown_resources


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
def int_service_resource_dep():
    @resource
    def get_int_service_resource():
        int_service = IntService.create()
        yield int_service
        int_service.close()

    return get_int_service_resource


async def get_int_service_async():
    int_service = IntService.create()
    yield int_service
    await int_service.aclose()


@pytest.fixture()
def int_service_async_resource_dep():
    @resource
    async def get_int_service_async_resource():
        int_service = IntService.create()
        yield int_service
        await int_service.aclose()

    return get_int_service_async_resource


def test_resolve_context_manager_sync():
    @inject
    def get_int(service: IntService = Provide(get_int_service)):
        assert service.closed is False
        return service

    int_service = get_int()
    assert isinstance(int_service, IntService)
    assert int_service.closed is True


def test_multiple_calls_to_context_manager_sync_return_different_values():
    @inject
    def get_int(service: IntService = Provide(get_int_service)):
        return service

    int_service_1 = get_int()
    int_service_2 = get_int()

    assert isinstance(int_service_1, IntService)
    assert isinstance(int_service_2, IntService)
    assert int_service_1 is not int_service_2


async def test_resolve_context_manager_async():
    @inject
    async def get_int(service: IntService = Provide(get_int_service_async)):
        assert service.closed is False
        return service

    int_service = await get_int()

    assert isinstance(int_service, IntService)
    assert int_service.closed is True


async def test_resolve_context_manager_sync_from_async_context():
    @inject
    async def get_int(service: IntService = Provide(get_int_service)):
        assert service.closed is False
        return service

    int_service = await get_int()

    assert isinstance(int_service, IntService)
    assert int_service.closed is True


async def test_multiple_calls_to_context_manager_async_return_different_values():
    @inject
    async def get_int(service: IntService = Provide(get_int_service_async)):
        return service

    int_service_1 = await get_int()
    int_service_2 = await get_int()

    assert isinstance(int_service_1, IntService)
    assert isinstance(int_service_2, IntService)
    assert int_service_1 is not int_service_2


def test_multiple_calls_to_resource_sync_return_same_values(int_service_resource_dep):
    @inject
    def get_int(service: IntService = Provide(int_service_resource_dep)):
        return service

    int_service_1 = get_int()
    int_service_2 = get_int()

    assert isinstance(int_service_1, IntService)
    assert int_service_1 is int_service_2


async def test_multiple_calls_to_resource_async_return_same_values(
    int_service_async_resource_dep,
):
    @inject
    async def get_int(service: IntService = Provide(int_service_async_resource_dep)):
        return service

    int_service_1 = await get_int()
    int_service_2 = await get_int()

    assert isinstance(int_service_1, IntService)
    assert int_service_1 is int_service_2


async def test_multiple_calls_to_resource_sync_from_async_context_return_same_values(
    int_service_resource_dep,
):
    @inject
    async def get_int(service: IntService = Provide(int_service_resource_dep)):
        return service

    int_service_1 = await get_int()
    int_service_2 = await get_int()

    assert isinstance(int_service_1, IntService)
    assert int_service_1 is int_service_2


def test_resolve_async_context_manager_from_sync_function_return_coroutine():
    @inject
    def get_async_dep(port: int = Provide(get_int_service_async)):
        return port

    result = get_async_dep()

    assert inspect.isasyncgen(result)
    assert result.__name__ == "get_int_service_async"


async def test_resolve_async_context_manager_from_sync_function_can_be_inited():
    @resource
    async def async_resource():
        int_service = IntService.create()
        yield int_service
        await int_service.aclose()

    @inject
    def get_async_dep(port: int = Provide(async_resource)):
        return port

    await init_resources()
    result = get_async_dep()

    assert isinstance(result, IntService)


def test_resource_doesnt_close_automatically(int_service_resource_dep):
    @inject
    def get_int(service: IntService = Provide(int_service_resource_dep)):
        return service

    int_service = get_int()
    assert int_service.closed is False


async def test_resource_doesnt_close_automatically_async(
    int_service_async_resource_dep,
):
    @inject
    async def get_int(service: IntService = Provide(int_service_async_resource_dep)):
        return service

    int_service = await get_int()
    assert int_service.closed is False


async def test_resource_doesnt_close_automatically_sync_from_async_context(
    int_service_resource_dep,
):
    @inject
    async def get_int(service: IntService = Provide(int_service_resource_dep)):
        return service

    int_service = await get_int()
    assert int_service.closed is False


def test_resource_can_be_closed_manually():
    @resource
    def async_resource():
        int_service = IntService.create()
        yield int_service
        int_service.close()

    @inject
    def get_async_dep(port: int = Provide(async_resource)):
        return port

    result = get_async_dep()
    assert result.closed is False

    shutdown_resources()

    assert result.closed is True


async def test_resource_can_be_closed_manually_async():
    @resource
    async def async_resource():
        int_service = IntService.create()
        yield int_service
        await int_service.aclose()

    @inject
    async def get_async_dep(port: int = Provide(async_resource)):
        return port

    result = await get_async_dep()
    assert result.closed is False

    await shutdown_resources()

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


def test_can_init_injected_resource():
    called = 0

    def get_42():
        return 42

    @resource
    @inject
    def my_resource(number: int = Provide(get_42)):
        assert number == 42
        nonlocal called
        called += 1
        return number

    Provide(my_resource)  # for register resource

    init_resources()

    assert called == 1


async def test_can_init_injected_resource_async():
    called = 0

    def get_42():
        return 42

    @resource
    @inject
    async def my_async_resource(number: int = Provide(get_42)):
        assert number == 42
        nonlocal called
        called += 1
        return number

    Provide(my_async_resource)  # for register resource

    await init_resources()

    assert called == 1


async def test_dont_init_not_used_resources():
    @resource
    async def not_used_resource():
        yield 1 / 0

    @resource
    async def used_resource():
        yield 42

    @inject
    def get_async_dep(num: int = Provide(used_resource)):
        return num

    await init_resources()
    result = get_async_dep()

    assert result == 42
