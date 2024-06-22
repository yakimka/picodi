from picodi import Provide, inject
from picodi.helpers import enter


def get_42():
    return 42


def test_enter_sync_gen(closeable):
    def gen():
        yield 42
        closeable.close()

    with enter(gen()) as val:
        assert val == 42
        assert closeable.is_closed is False

    assert closeable.is_closed is True


async def test_enter_async_gen(closeable):
    async def gen():
        yield 42
        closeable.close()

    async with enter(gen()) as val:
        assert val == 42
        assert closeable.is_closed is False

    assert closeable.is_closed is True


def test_enter_injected_sync_gen(closeable):
    @inject
    def gen(num: int = Provide(get_42)):
        yield num
        closeable.close()

    with enter(gen()) as val:
        assert val == 42
        assert closeable.is_closed is False

    assert closeable.is_closed is True


async def test_enter_injected_async_gen(closeable):
    @inject
    async def gen(num: int = Provide(get_42)):
        yield num
        closeable.close()

    async with enter(gen()) as val:
        assert val == 42
        assert closeable.is_closed is False

    assert closeable.is_closed is True
