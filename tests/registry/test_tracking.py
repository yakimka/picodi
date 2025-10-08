from picodi import Provide, SingletonScope, inject, registry
from picodi.helpers import resolve


def test_can_track_that_dependency_was_in_use():
    def get_unused():
        return "unused"  # pragma: no cover

    def get_in_use():
        return "in_use"

    @inject
    def service(dependency: str = Provide(get_in_use)):
        return dependency

    service()

    assert get_in_use in registry.touched
    assert get_unused not in registry.touched


async def test_can_track_that_dependency_was_in_use_async():
    async def get_unused():
        return "unused"  # pragma: no cover

    async def get_in_use():
        return "in_use"

    @inject
    async def service(dependency: str = Provide(get_in_use)):
        return dependency

    await service()

    assert get_in_use in registry.touched
    assert get_unused not in registry.touched


def test_can_track_that_transitive_dependency_was_in_use():
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
    assert get_in_use in registry.touched
    assert get_transitive in registry.touched
    assert get_unused not in registry.touched


async def test_can_track_that_transitive_dependency_was_in_use_async():
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
    assert get_in_use in registry.touched
    assert get_transitive in registry.touched
    assert get_unused not in registry.touched


async def test_can_track_that_overriden_dependency_was_in_use():
    async def get_abc_dependency():
        raise NotImplementedError  # pragma: no cover

    async def get_in_use():
        return "in_use"

    @inject
    async def service(dependency: str = Provide(get_abc_dependency)):
        return dependency

    with registry.override(get_abc_dependency, get_in_use):
        await service()

    assert get_in_use in registry.touched
    assert get_abc_dependency not in registry.touched


async def test_can_track_dependencies_resolved_by_enter_helper():
    async def get_42():
        return 42

    async with resolve(get_42) as val:
        assert val == 42

    assert get_42 in registry.touched


async def test_track_async_dependency_that_was_called_from_sync():
    async def get_async():
        return "async"  # pragma: no cover

    def get_sync(async_dep: str = Provide(get_async)):
        return async_dep

    @inject
    def service(dependency: str = Provide(get_sync)):
        return dependency

    service()

    assert get_sync in registry.touched
    assert get_async in registry.touched


async def test_can_track_singleton_dependencies_after_clearing_touch_cache():
    # Arrange
    @registry.set_scope(SingletonScope)
    def get_in_use():
        return "in_use"

    @inject
    def service(dependency: str = Provide(get_in_use)):
        return dependency

    service()
    assert get_in_use in registry.touched
    registry.clear_touched()
    assert not registry.touched

    # Act
    service()

    # Assert
    assert get_in_use in registry.touched


def test_can_clear_usage_data():
    # Arrange
    def get_in_use():
        return "in_use"

    @inject
    def service(dependency: str = Provide(get_in_use)):
        return dependency

    service()

    # Act
    registry.clear_touched()

    # Assert
    assert not registry.touched


def test_clearing_registry_also_cleared_touched_cache():
    # Arrange
    def get_in_use():
        return "in_use"

    @inject
    def service(dependency: str = Provide(get_in_use)):
        return dependency

    service()

    # Act
    registry._clear()  # noqa: SLF001

    # Assert
    assert not registry.touched
