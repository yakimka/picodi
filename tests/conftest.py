import pytest

from picodi import registry

pytest_plugins = [
    "picodi.integrations._pytest",
    "picodi.integrations._pytest_asyncio",
    "pytester",
]


@pytest.fixture(autouse=True)
async def _clear_registry():
    yield
    registry.clear()


@pytest.fixture()
def make_closeable():
    def maker():
        class Closeable:
            def __init__(self, closed: bool = False) -> None:
                self.is_closed = closed
                self.close_call_count = 0

            def close(self) -> None:
                self.close_call_count += 1
                self.is_closed = True

        return Closeable()

    return maker


@pytest.fixture()
def closeable(make_closeable):
    return make_closeable()
