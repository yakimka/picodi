from contextlib import asynccontextmanager, contextmanager

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
