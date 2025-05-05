import uuid

from picodi import Provide, SingletonScope, inject, registry


def test_can_set_scope_for_function_with_method_call():
    def get_uuid() -> str:
        return str(uuid.uuid4())

    @inject
    def service(val: str = Provide(get_uuid)):
        return val

    registry.add(get_uuid, SingletonScope)

    res1 = service()
    res2 = service()
    assert res1 == res2


def test_can_idempotently_add_dependency_for_init():
    call_count = 0

    @registry.set_scope(SingletonScope, auto_init=True)
    def get_uuid() -> str:
        nonlocal call_count
        call_count += 1
        return str(uuid.uuid4())

    registry.add_for_init([get_uuid])

    @inject
    def service(val: str = Provide(get_uuid)):
        return val

    registry.init()

    registry.add(get_uuid, SingletonScope)
    registry.add(get_uuid, SingletonScope)

    res1 = service()
    res2 = service()

    assert res1 == res2
    assert call_count == 1
