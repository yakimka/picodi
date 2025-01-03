from picodi import (
    Provide,
    SingletonScope,
    dependency,
    init_dependencies,
    inject,
    shutdown_dependencies,
)
from picodi.helpers import enter


async def test_transitive_dependency_injected_with_enter_closed_properly(closeable):
    # Arrange
    @dependency(scope_class=SingletonScope)
    async def get_dep_with_cleanup():
        yield 42
        closeable.close()

    @dependency(scope_class=SingletonScope)
    @inject
    async def get_dep_without_cleanup():
        async with enter(get_dep_with_cleanup) as dep_with_cleanup:
            yield dep_with_cleanup

    @inject
    async def service(
        dep_without_cleanup: int = Provide(get_dep_without_cleanup),
    ) -> int:
        return dep_without_cleanup

    # Act
    result = await service()
    assert closeable.is_closed is False
    await shutdown_dependencies()

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

    @dependency(scope_class=SingletonScope)
    @inject
    async def get_dep_without_cleanup():
        async with enter(get_dep_with_cleanup) as dep_with_cleanup:
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
    await shutdown_dependencies()

    # Assert
    assert result == 42
    assert closeable.close_call_count == 3


async def test_can_sync_enter_inited_async_singleton():
    @dependency(scope_class=SingletonScope, use_init_hook=True)
    async def dep():
        return 42

    await init_dependencies([dep])

    with enter(dep) as val:
        assert val == 42


def test_enter_cm_not_closes_singleton_scoped_deps(closeable):
    @dependency(scope_class=SingletonScope)
    def dep():
        yield 42
        closeable.close()

    init_dependencies([dep])

    with enter(dep) as val:
        assert val == 42

    assert closeable.is_closed is False
