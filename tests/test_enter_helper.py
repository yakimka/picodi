from picodi import Provide, SingletonScope, inject
from picodi.helpers import enter


def get_42():
    return 42


def test_enter_sync_gen(closeable):
    def dep():
        yield 42
        closeable.close()

    with enter(dep) as val:
        assert val == 42
        assert closeable.is_closed is False

    assert closeable.is_closed is True


async def test_enter_async_gen(closeable):
    async def dep():
        yield 42
        closeable.close()

    async with enter(dep) as val:
        assert val == 42
        assert closeable.is_closed is False

    assert closeable.is_closed is True


def test_enter_injected_sync_gen(closeable):
    @inject
    def dep(num: int = Provide(get_42)):
        yield num
        closeable.close()

    with enter(dep) as val:
        assert val == 42
        assert closeable.is_closed is False

    assert closeable.is_closed is True


async def test_enter_injected_async_gen(closeable):
    @inject
    async def dep(num: int = Provide(get_42)):
        yield num
        closeable.close()

    async with enter(dep) as val:
        assert val == 42
        assert closeable.is_closed is False

    assert closeable.is_closed is True


def test_enter_does_not_close_singleton_dependency(make_context, closeable):
    def dep():
        yield 42
        closeable.close()

    context = make_context((dep, SingletonScope))
    with context:
        with enter(dep) as val:
            assert val == 42
            assert closeable.is_closed is False

        assert closeable.is_closed is False


def test_enter_regular_dependency():
    def dep():
        return 42

    with enter(dep) as val:
        assert val == 42


async def test_enter_regular_dependency_async():
    async def dep():
        return 42

    async with enter(dep) as val:
        assert val == 42


async def test_enter_respects_context_override(make_context):
    async def dep():
        return 42  # pragma: no cover

    context = make_context()

    async with context:
        with context.override(dep, lambda: 43):  # noqa: SIM117
            with enter(dep) as val:
                assert val == 43
