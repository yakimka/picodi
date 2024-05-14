import pytest

from picodi import Provide, inject
from picodi.helpers import enter


class Closeable:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


@pytest.fixture()
def closeable():
    return Closeable()


def get_42():
    return 42


def test_enter_sync_gen(closeable):
    def gen():
        yield 42
        closeable.close()

    with enter(gen()) as val:
        assert val == 42
        assert closeable.closed is False

    assert closeable.closed is True


async def test_enter_async_gen(closeable):
    async def gen():
        yield 42
        closeable.close()

    async with enter(gen()) as val:
        assert val == 42
        assert closeable.closed is False

    assert closeable.closed is True


def test_enter_injected_sync_gen(closeable):
    @inject
    def gen(num: int = Provide(get_42)):
        yield num
        closeable.close()

    with enter(gen()) as val:
        assert val == 42
        assert closeable.closed is False

    assert closeable.closed is True


async def test_enter_injected_async_gen(closeable):
    @inject
    async def gen(num: int = Provide(get_42)):
        yield num
        closeable.close()

    async with enter(gen()) as val:
        assert val == 42
        assert closeable.closed is False

    assert closeable.closed is True
