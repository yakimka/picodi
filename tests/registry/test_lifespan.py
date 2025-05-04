import pytest

from picodi import Registry, SingletonScope


@pytest.fixture()
def registry() -> Registry:
    return Registry()


@pytest.fixture()
def resource(registry):
    state = {"inited": False, "closed": False}

    @registry.set_scope(scope_class=SingletonScope)
    def my_resource():
        state["inited"] = True
        yield state
        state["closed"] = True

    return state, my_resource


@pytest.fixture()
def async_resource(registry):
    state = {"inited": False, "closed": False}

    @registry.set_scope(scope_class=SingletonScope)
    async def my_resource():
        state["inited"] = True
        yield state
        state["closed"] = True

    return state, my_resource


def test_can_init_and_shutdown_sync(resource, registry):
    state, dep = resource
    registry.add_for_init([dep])

    @registry.lifespan()
    def service():
        assert state["inited"] is True
        assert state["closed"] is False

    service()

    assert state["inited"] is True
    assert state["closed"] is True


async def test_can_init_and_shutdown_async(async_resource, registry):
    state, dep = async_resource
    registry.add_for_init([dep])

    @registry.alifespan()
    async def service():
        assert state["inited"] is True
        assert state["closed"] is False

    await service()

    assert state["inited"] is True
    assert state["closed"] is True


def test_can_init_and_shutdown_sync_as_context_manager(resource, registry):
    state, dep = resource
    registry.add_for_init([dep])

    with registry.lifespan():
        assert state["inited"] is True
        assert state["closed"] is False

    assert state["inited"] is True
    assert state["closed"] is True


async def test_can_init_and_shutdown_async_as_context_manager(async_resource, registry):
    state, dep = async_resource
    registry.add_for_init([dep])

    async with registry.alifespan():
        assert state["inited"] is True
        assert state["closed"] is False

    assert state["inited"] is True
    assert state["closed"] is True
