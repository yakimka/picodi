import pytest

from picodi import (
    Provide,
    SingletonScope,
    dependency,
    init_dependencies,
    inject,
    registry,
    shutdown_dependencies,
)


def get_abc_settings() -> dict:
    raise NotImplementedError


def test_can_override_dependency_with_decorator():
    @inject
    def my_service(settings: dict = Provide(get_abc_settings)):
        return settings

    @registry.override(get_abc_settings)
    def real_settings():
        return {"real": "settings"}

    result = my_service()

    assert result == {"real": "settings"}


def test_can_clear_overriding():
    def get_settings() -> dict:
        return {"default": "settings"}

    @inject
    def my_service(settings: dict = Provide(get_settings)):
        return settings

    @registry.override(get_settings)
    def overridden_settings():
        return {"overridden": "settings"}  # pragma: no cover

    registry.override(get_settings, None)

    result = my_service()

    assert result == {"default": "settings"}


def test_can_override_dependency_with_call():
    @inject
    def my_service(settings: dict = Provide(get_abc_settings)):
        return settings

    def real_settings():
        return {"real": "settings"}

    registry.override(get_abc_settings, real_settings)

    result = my_service()

    assert result == {"real": "settings"}


def test_can_override_with_context_manager():
    def get_settings() -> dict:
        return {"default": "settings"}

    @inject
    def my_service(settings: dict = Provide(get_settings)):
        return settings

    with registry.override(get_settings, lambda: {"overridden": "settings"}):
        in_context_result = my_service()
    after_context_result = my_service()

    assert in_context_result == {"overridden": "settings"}
    assert after_context_result == {"default": "settings"}


def test_can_context_manager_return_state_to_previous_not_to_original():
    @inject
    def my_service(settings: dict = Provide(get_abc_settings)):
        return settings

    @registry.override(get_abc_settings)
    def first_override():
        return {"first": "override"}

    with registry.override(get_abc_settings, lambda: {"second": "override"}):
        in_context_result = my_service()
    after_context_result = my_service()

    assert in_context_result == {"second": "override"}
    assert after_context_result == {"first": "override"}


def test_overriding_overridden_dependency_dont_apply_to_original_dep():
    @inject
    def my_service(settings: dict = Provide(get_abc_settings)):
        return settings

    def first_override():
        return {"first": "override"}

    def second_override():
        return {"second": "override"}  # pragma: no cover

    registry.override(get_abc_settings, first_override)
    registry.override(first_override, second_override)

    result = my_service()

    assert result == {"first": "override"}


def test_can_clear_overrides():
    def original_func1() -> str:
        return "original_func1"

    def original_func2() -> str:
        return "original_func2"

    @inject
    def my_service(
        original1: str = Provide(original_func1),
        original2: str = Provide(original_func2),
    ):
        return original1, original2

    registry.override(original_func1, lambda: "overridden_func1")
    registry.override(original_func2, lambda: "overridden_func2")

    overriden_result = my_service()

    registry.clear_overrides()

    cleared_result = my_service()

    assert overriden_result == ("overridden_func1", "overridden_func2")
    assert cleared_result == ("original_func1", "original_func2")


def test_can_use_yield_dependency_in_override(closeable):
    @inject
    def my_service(settings: dict = Provide(get_abc_settings)):
        return settings

    def real_settings():
        yield {"real": "settings"}
        closeable.close()

    registry.override(get_abc_settings, real_settings)

    result = my_service()

    assert result == {"real": "settings"}
    assert closeable.is_closed is True


def test_can_use_dep_with_not_default_scope_class_in_override(closeable):
    @inject
    def my_service(settings: dict = Provide(get_abc_settings)):
        return settings

    @dependency(scope_class=SingletonScope)
    def real_settings():
        yield {"real": "settings"}
        closeable.close()

    registry.override(get_abc_settings, real_settings)

    result = my_service()

    assert result == {"real": "settings"}
    assert closeable.is_closed is False
    shutdown_dependencies()
    assert closeable.is_closed is True


async def test_can_use_async_dependency_in_override():
    @inject
    async def my_service(settings: dict = Provide(get_abc_settings)):
        return settings

    @registry.override(get_abc_settings)
    async def real_settings():
        return {"real": "settings"}

    result = await my_service()

    assert result == {"real": "settings"}


async def test_can_use_async_dep_with_not_default_scope_in_override_in_sync_context():
    @inject
    def my_service(settings: dict = Provide(get_abc_settings)):
        return settings

    @dependency(scope_class=SingletonScope)
    @registry.override(get_abc_settings)
    async def real_settings():
        return {"real": "settings"}

    await init_dependencies()

    result = my_service()

    assert result == {"real": "settings"}


def test_cant_override_dependency_with_itself():
    def get_settings() -> dict:
        return {"default": "settings"}

    with pytest.raises(ValueError, match="Cannot override a dependency with itself"):
        registry.override(get_settings, get_settings)
