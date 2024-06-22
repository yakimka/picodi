from picodi import Provide, SingletonScope, dependency, inject
from picodi.helpers import enter


def get_42():
    return 42


def test_enter_sync_gen(closeable):
    def gen():
        yield 42
        closeable.close()

    with enter(gen) as val:
        assert val == 42
        assert closeable.is_closed is False

    assert closeable.is_closed is True


async def test_enter_async_gen(closeable):
    async def gen():
        yield 42
        closeable.close()

    async with enter(gen) as val:
        assert val == 42
        assert closeable.is_closed is False

    assert closeable.is_closed is True


def test_enter_injected_sync_gen(closeable):
    @inject
    def gen(num: int = Provide(get_42)):
        yield num
        closeable.close()

    with enter(gen) as val:
        assert val == 42
        assert closeable.is_closed is False

    assert closeable.is_closed is True


async def test_enter_injected_async_gen(closeable):
    @inject
    async def gen(num: int = Provide(get_42)):
        yield num
        closeable.close()

    async with enter(gen) as val:
        assert val == 42
        assert closeable.is_closed is False

    assert closeable.is_closed is True


def test_singleton_sync_gen_not_closed(closeable):
    @dependency(scope_class=SingletonScope)
    def gen():
        yield 42
        closeable.close()

    with enter(gen) as val:
        assert val == 42
        assert closeable.is_closed is False

    assert closeable.is_closed is False


def test_enter_regular_dependency():
    def dep():
        return 42

    with enter(dep) as val:
        assert val == 42
