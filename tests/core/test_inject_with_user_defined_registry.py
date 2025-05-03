from uuid import uuid4

from picodi import Provide, Registry, SingletonScope, inject, registry


def get_uuid() -> str:
    return str(uuid4())


def test_use_user_defined_registry():
    custom_registry = Registry()
    custom_registry.add(get_uuid, scope_class=SingletonScope)

    @inject(registry=custom_registry)
    def with_custom_registry(uuid: int = Provide(get_uuid)) -> int:
        return uuid

    @inject
    def with_default_registry(uuid: int = Provide(get_uuid)) -> int:
        return uuid

    custom_registry_results = {with_custom_registry() for _ in range(100)}
    default_registry_results = {with_default_registry() for _ in range(100)}

    assert len(custom_registry_results) == 1
    assert len(default_registry_results) > 50


def test_multiple_registries_not_overlapping():
    custom_registry_1 = Registry()
    custom_registry_2 = Registry()

    custom_registry_1.add(get_uuid, scope_class=SingletonScope)
    custom_registry_2.add(get_uuid, scope_class=SingletonScope)
    registry.add(get_uuid, scope_class=SingletonScope)

    @inject(registry=custom_registry_1)
    def with_custom_registry_1(uuid: str = Provide(get_uuid)) -> str:
        return uuid

    @inject(registry=custom_registry_2)
    def with_custom_registry_2(uuid: str = Provide(get_uuid)) -> str:
        return uuid

    @inject
    def with_default_registry(uuid: str = Provide(get_uuid)) -> str:
        return uuid

    custom_registry_1_result = with_custom_registry_1()
    custom_registry_2_result = with_custom_registry_2()
    default_registry_result = with_default_registry()

    assert (
        len(
            {
                custom_registry_1_result,
                custom_registry_2_result,
                default_registry_result,
            }
        )
        == 3
    )
    assert custom_registry_1_result == with_custom_registry_1()
    assert custom_registry_2_result == with_custom_registry_2()
    assert default_registry_result == with_default_registry()

    custom_registry_1.shutdown()
    assert custom_registry_1_result != with_custom_registry_1()
    assert custom_registry_2_result == with_custom_registry_2()
    assert default_registry_result == with_default_registry()

    custom_registry_2.shutdown()
    assert custom_registry_2_result != with_custom_registry_2()
    assert default_registry_result == with_default_registry()

    registry.shutdown()
    assert default_registry_result != with_default_registry()


def test_direct_call_inside_decorated_function():
    custom_registry = Registry()
    custom_registry.add(get_uuid, scope_class=SingletonScope)

    @inject(registry=custom_registry)
    def with_custom_registry(uuid: str = Provide(get_uuid)) -> str:
        return uuid

    @inject(registry=custom_registry)
    def service(uuid: str = Provide(get_uuid)) -> tuple[str, str]:
        return uuid, with_custom_registry()

    uuid1, uuid2 = service()

    assert uuid1 == uuid2
