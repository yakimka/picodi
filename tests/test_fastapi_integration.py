import pytest
from fastapi import Depends, FastAPI
from fastapi.exceptions import FastAPIError
from fastapi.testclient import TestClient

from picodi import Provide, inject


class MyNumber:
    def __init__(self, number: int):
        self.value = number


@pytest.fixture()
def app():
    return FastAPI()


@pytest.fixture()
def client(app):
    return TestClient(app)


def test_fastapi_cant_use_provide_as_is(app):
    @inject
    def get_42() -> MyNumber:
        return MyNumber(42)

    with pytest.raises(FastAPIError, match="Invalid args for response field"):

        @app.get("/")
        @inject
        async def root(number: MyNumber = Provide(get_42)):
            return {"number": number}


def test_resolve_dependency_in_route(app, client):
    def get_42() -> MyNumber:
        return MyNumber(42)

    @app.get("/")
    @inject
    def root(number: MyNumber = Depends(Provide(get_42))):
        return {"number": number.value}

    response = client.get("/")

    assert response.json() == {"number": 42}


async def test_resolve_dependency_in_route_async(app, client):
    async def get_42() -> MyNumber:
        return MyNumber(42)

    @app.get("/")
    @inject
    async def root(number: MyNumber = Depends(Provide(get_42))):
        return {"number": number.value}

    response = client.get("/")

    assert response.json() == {"number": 42}


def test_resolve_mixed_dependency_in_route(app, client):
    async def get_42() -> MyNumber:
        return MyNumber(42)

    @inject
    async def get_by_slug(
        slug: str, number: MyNumber = Depends(Provide(get_42))
    ) -> dict[str, int]:
        return {slug: number.value}

    @app.get("/")
    @inject
    async def root(slug_result: dict[str, int] = Depends(get_by_slug)):
        return slug_result

    response = client.get("/", params={"slug": "meaning-of-life"})

    assert response.json() == {"meaning-of-life": 42}


def test_need_to_use_depends_only_in_view_not_in_nested_deps(app, client):
    async def get_42() -> int:
        return 42

    @inject
    async def get_number(value: int = Provide(get_42)) -> MyNumber:
        return MyNumber(value)

    class StringNumber:
        def __init__(self, number: MyNumber):
            self.value = str(number.value)

    @inject
    async def get_number_as_string(
        number: MyNumber = Provide(get_number),
    ) -> StringNumber:
        return StringNumber(number)

    @app.get("/")
    @inject
    async def root(
        string_number: StringNumber = Depends(Provide(get_number_as_string)),
    ):
        return {"nested": string_number.value}

    response = client.get("/")

    assert response.json() == {"nested": "42"}
