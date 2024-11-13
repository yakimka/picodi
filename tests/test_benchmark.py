import asyncio
from dataclasses import dataclass

import pytest

from picodi import Provide, inject

pytestmark = pytest.mark.benchmark_test


@pytest.fixture()
async def aio_benchmark(benchmark):
    # https://github.com/ionelmc/pytest-benchmark/issues/66#issuecomment-2058337929
    async def run_async_coroutine(func, *args, **kwargs):
        return await func(*args, **kwargs)

    def _wrapper(func, *args, **kwargs):
        if asyncio.iscoroutinefunction(func):

            def run_async():
                future = asyncio.ensure_future(
                    run_async_coroutine(func, *args, **kwargs)
                )
                return asyncio.get_event_loop().run_until_complete(future)

            return benchmark(run_async, *args, **kwargs)
        else:
            return benchmark(func, *args, **kwargs)

    return _wrapper


@dataclass(frozen=True)
class MySettings:
    http_client_base_url: str
    database_connection_string: str


my_settings = MySettings(
    http_client_base_url="http://example.com",
    database_connection_string="sqlite:///:memory:",
)


class MyHttpClient:
    def __init__(self, base_url: str):
        self.base_url = base_url


class MyDatabase:
    def __init__(self, connection_string: str):
        self.connection_string = connection_string


class MyRepository:
    def __init__(self, database: MyDatabase):
        self.database = database


class MyService:
    def __init__(self, http_client: MyHttpClient, repository: MyRepository):
        self.http_client = http_client
        self.repository = repository


def test_reference(benchmark):
    def create_http_client() -> MyHttpClient:
        return MyHttpClient(my_settings.http_client_base_url)

    def create_database() -> MyDatabase:
        return MyDatabase(my_settings.database_connection_string)

    def create_repository(database: MyDatabase) -> MyRepository:
        return MyRepository(database)

    def create_service(
        http_client: MyHttpClient, repository: MyRepository
    ) -> MyService:
        return MyService(http_client, repository)

    def create_all():
        http_client = create_http_client()
        database = create_database()
        repository = create_repository(database)
        return create_service(http_client, repository)

    result = benchmark(create_all)

    check_result(result)


def test_reference_async(aio_benchmark):
    async def create_http_client() -> MyHttpClient:
        return MyHttpClient(my_settings.http_client_base_url)

    async def create_database() -> MyDatabase:
        return MyDatabase(my_settings.database_connection_string)

    async def create_repository(database: MyDatabase) -> MyRepository:
        return MyRepository(database)

    async def create_service(
        http_client: MyHttpClient, repository: MyRepository
    ) -> MyService:
        return MyService(http_client, repository)

    async def create_all():
        http_client = await create_http_client()
        database = await create_database()
        repository = await create_repository(database)
        return await create_service(http_client, repository)

    result = aio_benchmark(create_all)

    check_result(result)


def test_picodi_injection(benchmark):
    def get_http_client() -> MyHttpClient:
        return MyHttpClient(my_settings.http_client_base_url)

    def get_database() -> MyDatabase:
        return MyDatabase(my_settings.database_connection_string)

    @inject
    def get_repository(database: MyDatabase = Provide(get_database)) -> MyRepository:
        return MyRepository(database)

    @inject
    def get_service(
        http_client: MyHttpClient = Provide(get_http_client),
        repository: MyRepository = Provide(get_repository),
    ) -> MyService:
        return MyService(http_client, repository)

    @inject
    def create_all(service: MyService = Provide(get_service)) -> MyService:
        return service

    result = benchmark(create_all)

    check_result(result)


def test_picodi_injection_async(aio_benchmark):
    async def get_http_client() -> MyHttpClient:
        return MyHttpClient(my_settings.http_client_base_url)

    async def get_database() -> MyDatabase:
        return MyDatabase(my_settings.database_connection_string)

    @inject
    async def get_repository(
        database: MyDatabase = Provide(get_database),
    ) -> MyRepository:
        return MyRepository(database)

    @inject
    async def get_service(
        http_client: MyHttpClient = Provide(get_http_client),
        repository: MyRepository = Provide(get_repository),
    ) -> MyService:
        return MyService(http_client, repository)

    @inject
    async def create_all(service: MyService = Provide(get_service)) -> MyService:
        return service

    result = aio_benchmark(create_all)

    check_result(result)


def check_result(result):
    __tracebackhide__ = True

    assert isinstance(result, MyService)
    assert result.http_client.base_url == my_settings.http_client_base_url
    connection_string = my_settings.database_connection_string
    assert result.repository.database.connection_string == connection_string