import pytest

from picodi import SingletonScope, dependency
from picodi.helpers import lifespan


@pytest.fixture()
def resource():
    state = {"inited": False, "closed": False}

    @dependency(scope_class=SingletonScope)
    def my_resource():
        state["inited"] = True
        yield state
        state["closed"] = True

    return state, my_resource


@pytest.fixture()
def async_resource():
    state = {"inited": False, "closed": False}

    @dependency(scope_class=SingletonScope)
    async def my_resource():
        state["inited"] = True
        yield state
        state["closed"] = True

    return state, my_resource


@pytest.mark.parametrize("decorator", [lifespan, lifespan.sync()])
def test_can_init_and_shutdown_sync(resource, decorator):
    state, _ = resource

    @decorator
    def service():
        assert state["inited"] is True
        assert state["closed"] is False

    service()

    assert state["inited"] is True
    assert state["closed"] is True


@pytest.mark.parametrize("decorator", [lifespan, lifespan.async_()])
async def test_can_init_and_shutdown_async(async_resource, decorator):
    state, _ = async_resource

    @decorator
    async def service():
        assert state["inited"] is True
        assert state["closed"] is False

    await service()

    assert state["inited"] is True
    assert state["closed"] is True


@pytest.mark.parametrize("manager", [lifespan, lifespan.sync])
def test_can_init_and_shutdown_sync_as_context_manager(resource, manager):
    state, _ = resource

    with manager():
        assert state["inited"] is True
        assert state["closed"] is False

    assert state["inited"] is True
    assert state["closed"] is True


@pytest.mark.parametrize("manager", [lifespan, lifespan.async_])
async def test_can_init_and_shutdown_async_as_context_manager(async_resource, manager):
    state, _ = async_resource

    async with manager():
        assert state["inited"] is True
        assert state["closed"] is False

    assert state["inited"] is True
    assert state["closed"] is True
