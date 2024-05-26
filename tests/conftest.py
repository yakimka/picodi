import pytest

from picodi import registry, shutdown_resources


@pytest.fixture(autouse=True)
async def _clear_registry():
    yield
    await shutdown_resources()
    registry.clear()


@pytest.fixture()
def closeable():
    class Closeable:
        def __init__(self, closed: bool = False) -> None:
            self.is_closed = closed
            self.close_call_count = 0

        def close(self) -> None:
            self.close_call_count += 1
            self.is_closed = True

    return Closeable()
