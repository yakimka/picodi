import pytest

from picodi import Provide, SingletonScope, inject


def get_abc_settings() -> dict:
    raise NotImplementedError


def test_can_override_dependency_with_decorator(make_context):
    @inject
    def my_service(settings: dict = Provide(get_abc_settings)):
        return settings

    with make_context() as context:

        @context.override(get_abc_settings)
        def real_settings():
            return {"real": "settings"}

        result = my_service()

    assert result == {"real": "settings"}


def test_can_clear_overriding(make_context):
    def get_settings() -> dict:
        return {"default": "settings"}

    @inject
    def my_service(settings: dict = Provide(get_settings)):
        return settings

    with make_context() as context:

        @context.override(get_settings)
        def overridden_settings():
            return {"overridden": "settings"}  # pragma: no cover

        context.override(get_settings, None)

        result = my_service()

    assert result == {"default": "settings"}


def test_can_override_dependency_with_call(make_context):
    @inject
    def my_service(settings: dict = Provide(get_abc_settings)):
        return settings

    def real_settings():
        return {"real": "settings"}

    with make_context() as context:
        context.override(get_abc_settings, real_settings)

        result = my_service()

    assert result == {"real": "settings"}


def test_can_override_with_context_manager(make_context):
    def get_settings() -> dict:
        return {"default": "settings"}

    @inject
    def my_service(settings: dict = Provide(get_settings)):
        return settings

    with make_context() as context:
        with context.override(get_settings, lambda: {"overridden": "settings"}):
            in_context_result = my_service()
        after_context_result = my_service()

    assert in_context_result == {"overridden": "settings"}
    assert after_context_result == {"default": "settings"}


def test_can_context_manager_return_state_to_previous_not_to_original(make_context):
    @inject
    def my_service(settings: dict = Provide(get_abc_settings)):
        return settings

    with make_context() as context:

        @context.override(get_abc_settings)
        def first_override():
            return {"first": "override"}

        with context.override(get_abc_settings, lambda: {"second": "override"}):
            in_context_result = my_service()
        after_context_result = my_service()

    assert in_context_result == {"second": "override"}
    assert after_context_result == {"first": "override"}


def test_override_raises_error_when_overriding_an_override(make_context):
    @inject
    def my_service(settings: dict = Provide(get_abc_settings)):
        return settings  # pragma: no cover

    def first_override():
        return {"first": "override"}  # pragma: no cover

    def second_override():
        return {"second": "override"}  # pragma: no cover

    with make_context() as context:
        context.override(get_abc_settings, first_override)

        with pytest.raises(
            ValueError, match="Cannot override an overridden dependency"
        ):
            context.override(first_override, second_override)


def test_can_clear_overrides(make_context):
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

    with make_context() as context:
        context.override(original_func1, lambda: "overridden_func1")
        context.override(original_func2, lambda: "overridden_func2")

        overriden_result = my_service()

        context.clear_overrides()

        cleared_result = my_service()

    assert overriden_result == ("overridden_func1", "overridden_func2")
    assert cleared_result == ("original_func1", "original_func2")


def test_can_use_yield_dependency_in_override(make_context, closeable):
    @inject
    def my_service(settings: dict = Provide(get_abc_settings)):
        return settings

    def real_settings():
        yield {"real": "settings"}
        closeable.close()

    with make_context() as context:
        context.override(get_abc_settings, real_settings)

        result = my_service()

    assert result == {"real": "settings"}
    assert closeable.is_closed is True


def test_override_works_with_dependency_registered_with_custom_scope(
    make_context, closeable
):
    @inject
    def my_service(settings: dict = Provide(get_abc_settings)):
        return settings

    def real_settings():
        yield {"real": "settings"}
        closeable.close()

    with make_context((real_settings, SingletonScope)) as context:
        context.override(get_abc_settings, real_settings)

        result = my_service()
        assert closeable.is_closed is False

    assert result == {"real": "settings"}
    assert closeable.is_closed is True


async def test_can_use_async_dependency_in_override(make_context):
    @inject
    async def my_service(settings: dict = Provide(get_abc_settings)):
        return settings

    async def real_settings():
        return {"real": "settings"}

    async with make_context() as context:
        context.override(get_abc_settings, real_settings)

        result = await my_service()

    assert result == {"real": "settings"}


async def test_override_with_initialized_async_singleton_resolves_in_sync_context(
    make_context,
):
    @inject
    def my_service(settings: dict = Provide(get_abc_settings)):
        return settings

    async def real_settings():
        return {"real": "settings"}

    context = make_context(
        (real_settings, SingletonScope), init_dependencies=[real_settings]
    )
    async with context:
        context.override(get_abc_settings, real_settings)

        result = my_service()

    assert result == {"real": "settings"}


def test_cant_override_dependency_with_itself(make_context):
    def get_settings() -> dict:
        return {"default": "settings"}  # pragma: no cover

    with make_context() as context:
        with pytest.raises(
            ValueError, match="Cannot override a dependency with itself"
        ):
            context.override(get_settings, get_settings)


def test_can_override_with_injected_dep(make_context):
    @inject
    def original_dep(num: int = Provide(lambda: 1)):  # pragma: no cover
        return num

    @inject
    def overriding_dep(num2: int = Provide(lambda: 42)):
        return num2

    @inject
    def my_service(dep: int = Provide(original_dep)):
        return dep

    with make_context() as context:
        with context.override(original_dep, overriding_dep):
            result = my_service()

    assert result == 42


def test_can_override_with_zero_arguments_function(make_context):
    @inject
    def original_dep(num: int = Provide(lambda: 1)):  # pragma: no cover
        return num

    def overriding_dep():
        return 42

    @inject
    def my_service(dep: int = Provide(original_dep)):
        return dep

    with make_context() as context:
        with context.override(original_dep, overriding_dep):
            result = my_service()

    assert result == 42


async def test_can_override_with_injected_dep_async(make_context):
    @inject
    async def original_dep(num: int = Provide(lambda: 1)):  # pragma: no cover
        return num

    @inject
    async def overriding_dep(num2: int = Provide(lambda: 42)):
        return num2

    @inject
    async def my_service(dep: int = Provide(original_dep)):
        return dep

    async with make_context() as context:
        with context.override(original_dep, overriding_dep):
            result = await my_service()

    assert result == 42


async def test_can_override_with_zero_arguments_function_async(make_context):
    @inject
    async def original_dep(num: int = Provide(lambda: 1)):  # pragma: no cover
        return num

    async def overriding_dep():
        return 42

    @inject
    async def my_service(dep: int = Provide(original_dep)):
        return dep

    async with make_context() as context:
        with context.override(original_dep, overriding_dep):
            result = await my_service()

    assert result == 42


def test_can_override_deeply_nested_dep(make_context):
    @inject
    async def original_dep(num: int = Provide(lambda: 1)):  # pragma: no cover
        return num

    def overriding_dep():
        return 42

    @inject
    def third_level_dep(dep4: int = Provide(original_dep)):
        return dep4

    @inject
    def second_level_dep(dep3: int = Provide(third_level_dep)):
        return dep3

    @inject
    def first_level_dep(dep2: int = Provide(second_level_dep)):
        return dep2

    @inject
    def my_service(my_dep: int = Provide(first_level_dep)):
        return my_dep

    with make_context() as context:
        with context.override(original_dep, overriding_dep):
            result = my_service()

    assert result == 42
