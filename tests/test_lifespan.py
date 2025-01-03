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


@pytest.mark.parametrize("decorator", [lifespan, lifespan.sync])
def test_can_init_and_shutdown_sync(resource, decorator):
    state, dep = resource

    @decorator(dependencies_for_init=[dep])
    def service():
        assert state["inited"] is True
        assert state["closed"] is False

    service()

    assert state["inited"] is True
    assert state["closed"] is True


@pytest.mark.parametrize("decorator", [lifespan, lifespan.async_])
async def test_can_init_and_shutdown_async(async_resource, decorator):
    state, dep = async_resource

    @decorator(dependencies_for_init=[dep])
    async def service():
        assert state["inited"] is True
        assert state["closed"] is False

    await service()

    assert state["inited"] is True
    assert state["closed"] is True


def test_can_init_and_shutdown_sync_as_context_manager(resource):
    state, dep = resource

    with lifespan.sync(dependencies_for_init=[dep]):
        assert state["inited"] is True
        assert state["closed"] is False

    assert state["inited"] is True
    assert state["closed"] is True


async def test_can_init_and_shutdown_async_as_context_manager(async_resource):
    state, dep = async_resource

    async with lifespan.async_(dependencies_for_init=[dep]):
        assert state["inited"] is True
        assert state["closed"] is False

    assert state["inited"] is True
    assert state["closed"] is True


@pytest.mark.parametrize("decorator", [lifespan, lifespan.sync])
def test_skip_initialization(resource, decorator):
    state, dep = resource

    @decorator(dependencies_for_init=None)
    def service():
        pass

    service()

    assert state["inited"] is False


@pytest.mark.parametrize("decorator", [lifespan, lifespan.async_])
async def test_skip_initialization_async(async_resource, decorator):
    state, dep = async_resource

    @decorator(dependencies_for_init=None)
    async def service():
        pass

    await service()

    assert state["inited"] is False


@pytest.mark.parametrize("decorator", [lifespan, lifespan.sync])
def test_skip_shutdown(resource, decorator):
    state, dep = resource

    @decorator(dependencies_for_init=[dep], shutdown_scope_class=None)
    def service():
        pass

    service()

    assert state["inited"] is True
    assert state["closed"] is False


@pytest.mark.parametrize("decorator", [lifespan, lifespan.async_])
async def test_skip_shutdown_async(async_resource, decorator):
    state, dep = async_resource

    @decorator(dependencies_for_init=[dep], shutdown_scope_class=None)
    async def service():
        pass

    await service()

    assert state["inited"] is True
    assert state["closed"] is False
