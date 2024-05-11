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
        raise NotImplementedError

    @inject
    def my_service(settings: dict = Provide(get_settings)):
        return settings

    with registry.override(get_settings, lambda: {"real": "settings"}):
        result = my_service()

    assert result == {"real": "settings"}
