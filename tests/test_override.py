from picodi import Provide, inject, registry


def test_can_override_dependency_with_decorator():
    def get_settings() -> dict:
        raise NotImplementedError

    @inject
    def my_service(settings: dict = Provide(get_settings)):
        return settings

    @registry.override(get_settings)
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
        return {"overridden": "settings"}

    registry.override(get_settings, None)

    result = my_service()

    assert result == {"default": "settings"}


def test_can_override_dependency_with_call():
    def get_settings() -> dict:
        raise NotImplementedError

    @inject
    def my_service(settings: dict = Provide(get_settings)):
        return settings

    def real_settings():
        return {"real": "settings"}

    registry.override(get_settings, real_settings)

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
    def get_settings() -> dict:
        raise NotImplementedError

    @inject
    def my_service(settings: dict = Provide(get_settings)):
        return settings

    @registry.override(get_settings)
    def first_override():
        return {"first": "override"}

    with registry.override(get_settings, lambda: {"second": "override"}):
        in_context_result = my_service()
    after_context_result = my_service()

    assert in_context_result == {"second": "override"}
    assert after_context_result == {"first": "override"}


def test_overriding_overridden_dependency_dont_apply_to_original_dep():
    def get_settings() -> dict:
        raise NotImplementedError

    @inject
    def my_service(settings: dict = Provide(get_settings)):
        return settings

    def first_override():
        return {"first": "override"}

    def second_override():
        return {"second": "override"}

    registry.override(get_settings, first_override)
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
