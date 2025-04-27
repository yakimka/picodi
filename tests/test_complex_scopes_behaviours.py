from picodi import Provide, SingletonScope, inject
from picodi.helpers import enter


async def test_transitive_singleton_dependency_via_enter_closes_on_context_exit(
    make_context, closeable
):
    # Arrange
    async def get_dep_with_cleanup():
        yield 42
        closeable.close()

    @inject
    async def get_dep_without_cleanup():
        async with enter(get_dep_with_cleanup) as dep_with_cleanup:
            yield dep_with_cleanup

    @inject
    async def service(
        dep_without_cleanup: int = Provide(get_dep_without_cleanup),
    ) -> int:
        return dep_without_cleanup

    context = make_context(
        (get_dep_with_cleanup, SingletonScope),
        (get_dep_without_cleanup, SingletonScope),
    )

    # Act
    async with context:
        result = await service()
        assert closeable.is_closed is False

    # Assert
    assert result == 42
    assert closeable.is_closed is True


async def test_transitive_local_dependency_injected_from_singleton_acts_like_singleton(
    make_context,
    closeable,
):
    # Arrange
    async def get_dep_with_cleanup():
        yield 42
        closeable.close()

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

    context = make_context(
        (get_dep_without_cleanup, SingletonScope),
    )

    # Act
    async with context:
        result = await service()
        assert closeable.is_closed is False
        await service2()
        await service2()
        assert closeable.close_call_count == 2

    # Assert
    assert result == 42
    assert closeable.close_call_count == 3


async def test_can_sync_enter_inited_async_singleton(make_context):
    async def dep():
        return 42

    context = make_context(
        (dep, SingletonScope),
        init_dependencies=[dep],
    )
    async with context:
        with enter(dep) as val:
            assert val == 42


def test_enter_cm_not_closes_singleton_scoped_deps(make_context, closeable):
    def dep():
        yield 42
        closeable.close()

    context = make_context(
        (dep, SingletonScope),
        init_dependencies=[dep],
    )

    with context:
        with enter(dep) as val:
            assert val == 42
        assert closeable.is_closed is False
