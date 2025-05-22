from contextlib import asynccontextmanager, contextmanager

import pytest

from picodi import Provide, inject


def get_meaning_of_life() -> int:
    return 42


def test_using_inject_decorator_with_contextmanager():
    @contextmanager
    @inject
    def my_manager(num: int = Provide(get_meaning_of_life)):
        yield num

    with my_manager() as num:
        assert num == 42


async def test_using_inject_decorator_with_asynccontextmanager():
    @asynccontextmanager
    @inject
    async def my_manager(num: int = Provide(get_meaning_of_life)):
        yield num

    async with my_manager() as num:
        assert num == 42


def test_resources_closed_after_context_manager_close(closeable):
    def get_yield_dep():
        yield closeable
        closeable.close()

    @contextmanager
    @inject
    def my_manager(dep=Provide(get_yield_dep)):
        yield
        assert dep.is_closed is False

    with my_manager():
        assert closeable.is_closed is False

    assert closeable.is_closed is True


async def test_resources_closed_after_context_manager_close_async(closeable):
    async def get_yield_dep():
        yield closeable
        closeable.close()

    @asynccontextmanager
    @inject
    async def my_manager(dep=Provide(get_yield_dep)):
        yield
        assert dep.is_closed is False

    async with my_manager():
        assert closeable.is_closed is False

    assert closeable.is_closed is True


def test_resources_are_closed_even_if_exception_raised(closeable):
    def get_yield_dep():
        try:
            yield closeable
        finally:
            closeable.close()

    @contextmanager
    @inject
    def my_manager(dep=Provide(get_yield_dep)):  # noqa: U100
        yield

    with pytest.raises(ValueError, match="Something went wrong"):  # noqa: PT012, SIM117
        with my_manager():
            assert closeable.is_closed is False
            raise ValueError("Something went wrong")

    assert closeable.is_closed is True


async def test_resources_are_closed_even_if_exception_raised_async(closeable):
    async def get_yield_dep():
        try:
            yield closeable
        finally:
            closeable.close()

    @asynccontextmanager
    @inject
    async def my_manager(dep=Provide(get_yield_dep)):
        assert dep.is_closed is False
        yield "my_manager_result"

    with pytest.raises(ValueError, match="Something went wrong"):  # noqa: PT012
        async with my_manager():
            assert closeable.is_closed is False
            raise ValueError("Something went wrong")

    assert closeable.is_closed is True


def test_resources_not_closed_without_finally_block(closeable):
    def get_yield_dep():
        yield closeable
        closeable.close()  # pragma: no cover

    @contextmanager
    @inject
    def my_manager(dep=Provide(get_yield_dep)):
        assert dep.is_closed is False
        yield "my_manager_result"

    with pytest.raises(ValueError, match="Something went wrong"):  # noqa: PT012, SIM117
        with my_manager():
            assert closeable.is_closed is False
            raise ValueError("Something went wrong")

    assert closeable.is_closed is False


async def test_resources_not_closed_without_finally_block_async(closeable):
    async def get_yield_dep():
        yield closeable
        closeable.close()  # pragma: no cover

    @asynccontextmanager
    @inject
    async def my_manager(dep=Provide(get_yield_dep)):
        assert dep.is_closed is False
        yield "my_manager_result"

    with pytest.raises(ValueError, match="Something went wrong"):  # noqa: PT012
        async with my_manager():
            assert closeable.is_closed is False
            raise ValueError("Something went wrong")

    assert closeable.is_closed is False


def test_yield_dep_dont_close_while_parent_not_close(closeable):
    def get_yield_dep():
        yield "my_dep"
        closeable.close()

    @contextmanager
    @inject
    def my_manager(dep=Provide(get_yield_dep)):
        assert closeable.is_closed is False
        yield dep
        raise ValueError("Should not be raised")  # pragma: no cover

    manager = my_manager()

    result = manager.__enter__()

    assert result == "my_dep"
    assert closeable.is_closed is False


async def test_yield_dep_dont_close_while_parent_not_close_async(closeable):
    async def get_yield_dep():
        yield "my_dep"
        closeable.close()

    @asynccontextmanager
    @inject
    async def my_manager(dep=Provide(get_yield_dep)):
        assert closeable.is_closed is False
        yield dep
        raise ValueError("Should not be raised")  # pragma: no cover

    manager = my_manager()

    result = await manager.__aenter__()

    assert result == "my_dep"
    assert closeable.is_closed is False


def test_can_use_context_manager_as_dependency():
    @contextmanager
    def get_int():
        yield 42

    @inject
    def service(val: int = Provide(get_int)) -> int:
        return val

    result = service()

    assert result == 42


async def test_can_use_async_context_manager_as_dependency():
    @asynccontextmanager
    async def get_int():
        yield 42

    @inject
    async def service(val: int = Provide(get_int)) -> int:
        return val

    result = await service()

    assert result == 42


async def test_can_use_custom_async_context_manager_as_return_value_of_dependency():
    class CustomAsyncContextManager:
        def __init__(self, value):
            self.value = value

        async def __aenter__(self):
            pass

        async def __aexit__(self, exc_type, exc_val, exc_tb):
            pass

    async def get_my_cm():
        return CustomAsyncContextManager(42)

    @inject
    async def service(dep=Provide(get_my_cm)):
        return dep

    result = await service()

    assert result.value == 42
