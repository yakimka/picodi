import pytest

from picodi import Provide, SingletonScope, inject
from picodi.helpers import enter


@pytest.fixture()
def context(make_context):
    with make_context() as ctx:
        yield ctx


def test_tracks_directly_used_dependency(context):
    def get_unused():
        return "unused"  # pragma: no cover

    def get_in_use():
        return "in_use"

    @inject
    def service(dependency: str = Provide(get_in_use)):
        return dependency

    service()

    assert get_in_use in context.touched
    assert get_unused not in context.touched


async def test_tracks_directly_used_dependency_async(context):
    async def get_unused():
        return "unused"  # pragma: no cover

    async def get_in_use():
        return "in_use"

    @inject
    async def service(dependency: str = Provide(get_in_use)):
        return dependency

    await service()

    assert get_in_use in context.touched
    assert get_unused not in context.touched


def test_tracks_transitively_used_dependency(context):
    def get_unused():
        return "unused"  # pragma: no cover

    def get_transitive():
        return "transitive"

    @inject
    def get_in_use(transitive: str = Provide(get_transitive)):
        return f"in_use {transitive}"

    @inject
    def service(dependency: str = Provide(get_in_use)):
        return dependency

    result = service()

    assert result == "in_use transitive"
    assert get_in_use in context.touched
    assert get_transitive in context.touched
    assert get_unused not in context.touched


async def test_tracks_transitively_used_dependency_async(context):
    async def get_unused():
        return "unused"  # pragma: no cover

    async def get_transitive():
        return "transitive"

    @inject
    async def get_in_use(transitive: str = Provide(get_transitive)):
        return f"in_use {transitive}"

    @inject
    async def service(dependency: str = Provide(get_in_use)):
        return dependency

    result = await service()

    assert result == "in_use transitive"
    assert get_in_use in context.touched
    assert get_transitive in context.touched
    assert get_unused not in context.touched


async def test_tracks_override_dependency_not_original(context):
    async def get_abc_dependency():
        raise NotImplementedError  # pragma: no cover

    @context.override(get_abc_dependency)
    async def get_in_use():
        return "in_use"

    @inject
    async def service(dependency: str = Provide(get_abc_dependency)):
        return dependency

    await service()

    assert get_in_use in context.touched
    assert get_abc_dependency not in context.touched


async def test_can_track_dependencies_resolved_by_enter_helper(context):
    async def get_42():
        return 42

    async with enter(get_42) as val:
        assert val == 42

    assert get_42 in context.touched


async def test_track_async_dependency_that_was_called_from_sync(context):
    async def get_async():
        return "async"  # pragma: no cover

    def get_sync(async_dep: str = Provide(get_async)):
        return async_dep

    @inject
    def service(dependency: str = Provide(get_sync)):
        return dependency

    service()

    assert get_sync in context.touched
    assert get_async in context.touched


async def test_can_track_singleton_dependencies_after_clearing_touch_cache(
    make_context,
):
    # Arrange
    def get_in_use():
        return "in_use"

    @inject
    def service(dependency: str = Provide(get_in_use)):
        return dependency

    with make_context((get_in_use, SingletonScope)) as ctx:
        service()
        assert get_in_use in ctx.touched
        ctx.clear_touched()
        assert not ctx.touched

        # Act
        service()

        # Assert
        assert get_in_use in ctx.touched


def test_can_clear_usage_data(context):
    # Arrange
    def get_in_use():
        return "in_use"

    @inject
    def service(dependency: str = Provide(get_in_use)):
        return dependency

    service()

    # Act
    context.clear_touched()

    # Assert
    assert not context.touched
