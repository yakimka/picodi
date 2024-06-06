from contextlib import asynccontextmanager, contextmanager

from picodi import Provide, inject


def get_meaning_of_life() -> int:
    return 42


def test_using_inject_decorator_with_contextmanager():
    @inject
    @contextmanager
    def my_manager(num: int = Provide(get_meaning_of_life)):
        yield num

    with my_manager() as num:
        assert num == 42


async def test_using_inject_decorator_with_asynccontextmanager():
    @inject
    @asynccontextmanager
    async def my_manager(num: int = Provide(get_meaning_of_life)):
        yield num

    async with my_manager() as num:
        assert num == 42
