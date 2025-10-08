from picodi import Provide, SingletonScope, inject, registry
from picodi.helpers import resolve


def get_42():
    return 42


def test_resolve_sync_gen(closeable):
    def dep():
        yield 42
        closeable.close()

    with resolve(dep) as val:
        assert val == 42
        assert closeable.is_closed is False

    assert closeable.is_closed is True


async def test_resolve_async_gen(closeable):
    async def dep():
        yield 42
        closeable.close()

    async with resolve(dep) as val:
        assert val == 42
        assert closeable.is_closed is False

    assert closeable.is_closed is True


def test_resolve_injected_sync_gen(closeable):
    @inject
    def dep(num: int = Provide(get_42)):
        yield num
        closeable.close()

    with resolve(dep) as val:
        assert val == 42
        assert closeable.is_closed is False

    assert closeable.is_closed is True


async def test_resolve_injected_async_gen(closeable):
    @inject
    async def dep(num: int = Provide(get_42)):
        yield num
        closeable.close()

    async with resolve(dep) as val:
        assert val == 42
        assert closeable.is_closed is False

    assert closeable.is_closed is True


def test_singleton_sync_gen_not_closed(closeable):
    @registry.set_scope(SingletonScope)
    def dep():
        yield 42
        closeable.close()

    with resolve(dep) as val:
        assert val == 42
        assert closeable.is_closed is False

    assert closeable.is_closed is False


def test_resolve_regular_dependency():
    def dep():
        return 42

    with resolve(dep) as val:
        assert val == 42


async def test_resolve_regular_dependency_async():
    async def dep():
        return 42

    async with resolve(dep) as val:
        assert val == 42


async def test_can_use_override_resolve_dependency():
    async def dep():
        return 42  # pragma: no cover

    with registry.override(dep, lambda: 43):
        with resolve(dep) as val:
            assert val == 43
