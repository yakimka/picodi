from picodi import Provide, SingletonScope, dependency, inject, registry
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


def test_singleton_sync_gen_not_closed(closeable):
    @dependency(scope_class=SingletonScope)
    def dep():
        yield 42
        closeable.close()

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


async def test_can_use_override_enter_dependency():
    async def dep():
        return 42

    with registry.override(dep, lambda: 43):  # noqa: SIM117
        with enter(dep) as val:
            assert val == 43
