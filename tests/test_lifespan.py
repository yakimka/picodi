import pytest

from picodi import SingletonScope, dependency
from picodi.helpers import lifespan


@pytest.fixture()
def resource():
    state = {"inited": False, "closed": False}

    @dependency(scope_class=SingletonScope, use_init_hook=True)
    def my_resource():
        state["inited"] = True
        yield state
        state["closed"] = True

    return state, my_resource


@pytest.fixture()
def async_resource():
    state = {"inited": False, "closed": False}

    @dependency(scope_class=SingletonScope, use_init_hook=True)
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


def test_can_init_and_shutdown_sync_as_context_manager(resource):
    state, _ = resource

    with lifespan.sync():
        assert state["inited"] is True
        assert state["closed"] is False

    assert state["inited"] is True
    assert state["closed"] is True


async def test_can_init_and_shutdown_async_as_context_manager(async_resource):
    state, _ = async_resource

    async with lifespan.async_():
        assert state["inited"] is True
        assert state["closed"] is False

    assert state["inited"] is True
    assert state["closed"] is True


@pytest.mark.parametrize("decorator", [lifespan, lifespan.sync])
def test_skip_initialization(resource, decorator):
    state, _ = resource

    @decorator(init_scope_class=None)
    def service():
        pass

    service()

    assert state["inited"] is False


@pytest.mark.parametrize("decorator", [lifespan, lifespan.async_])
async def test_skip_initialization_async(async_resource, decorator):
    state, _ = async_resource

    @decorator(init_scope_class=None)
    async def service():
        pass

    await service()

    assert state["inited"] is False


@pytest.mark.parametrize("decorator", [lifespan, lifespan.sync])
def test_skip_shutdown(resource, decorator):
    state, _ = resource

    @decorator(shutdown_scope_class=None)
    def service():
        pass

    service()

    assert state["inited"] is True
    assert state["closed"] is False


@pytest.mark.parametrize("decorator", [lifespan, lifespan.async_])
async def test_skip_shutdown_async(async_resource, decorator):
    state, _ = async_resource

    @decorator(shutdown_scope_class=None)
    async def service():
        pass

    await service()

    assert state["inited"] is True
    assert state["closed"] is False
