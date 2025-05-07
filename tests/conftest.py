import pytest

from picodi import registry

pytest_plugins = ["pytester"]


def pytest_addoption(parser):
    parser.addoption(
        "--run-benchmarks",
        action="store_true",
        default=False,
        help="Run benchmark tests",
    )


def pytest_collection_modifyitems(config, items):
    is_benchmark_run = config.getoption("--run-benchmarks")
    for item in items:
        if is_benchmark_run and "benchmark_test" not in item.keywords:
            skipper = pytest.mark.skip(
                reason="Only run when --run-benchmarks is not given"
            )
            item.add_marker(skipper)
        elif not is_benchmark_run and "benchmark_test" in item.keywords:
            skipper = pytest.mark.skip(reason="Only run when --run-benchmarks is given")
            item.add_marker(skipper)


@pytest.fixture(autouse=True)
async def _cleanup():
    yield
    await registry.shutdown()


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
