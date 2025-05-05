from picodi import Provide, SingletonScope, inject, registry
from picodi.helpers import resolve


async def test_transitive_dependency_injected_with_enter_closed_properly(closeable):
    # Arrange
    @registry.set_scope(SingletonScope)
    async def get_dep_with_cleanup():
        yield 42
        closeable.close()

    @registry.set_scope(SingletonScope)
    @inject
    async def get_dep_without_cleanup():
        async with resolve(get_dep_with_cleanup) as dep_with_cleanup:
            yield dep_with_cleanup

    @inject
    async def service(
        dep_without_cleanup: int = Provide(get_dep_without_cleanup),
    ) -> int:
        return dep_without_cleanup

    # Act
    result = await service()
    assert closeable.is_closed is False
    await registry.shutdown()

    # Assert
    assert result == 42
    assert closeable.is_closed is True


async def test_transitive_local_dependency_injected_from_singleton_acts_like_singleton(
    closeable,
):
    # Arrange
    async def get_dep_with_cleanup():
        yield 42
        closeable.close()

    @registry.set_scope(SingletonScope)
    @inject
    async def get_dep_without_cleanup():
        async with resolve(get_dep_with_cleanup) as dep_with_cleanup:
            yield dep_with_cleanup

    @inject
    async def service(
        dep_without_cleanup: int = Provide(get_dep_without_cleanup),
    ) -> int:
        return dep_without_cleanup

    @inject
    async def service2(dep_with_cleanup: int = Provide(get_dep_with_cleanup)) -> int:
        return dep_with_cleanup

    # Act
    result = await service()
    assert closeable.is_closed is False
    await service2()
    await service2()
    assert closeable.close_call_count == 2
    await registry.shutdown()

    # Assert
    assert result == 42
    assert closeable.close_call_count == 3


async def test_can_sync_enter_inited_async_singleton():
    @registry.set_scope(SingletonScope)
    async def dep():
        return 42

    await registry.init([dep])

    with resolve(dep) as val:
        assert val == 42


def test_enter_cm_not_closes_singleton_scoped_deps(closeable):
    @registry.set_scope(SingletonScope)
    def dep():
        yield 42
        closeable.close()

    registry.init([dep])

    with resolve(dep) as val:
        assert val == 42

    assert closeable.is_closed is False
