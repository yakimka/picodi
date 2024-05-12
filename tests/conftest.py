import pytest

from picodi import registry, shutdown_resources


@pytest.fixture(autouse=True)
async def _clear_registry():
    yield
    await shutdown_resources()
    registry.clear()
