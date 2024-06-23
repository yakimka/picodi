from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.exceptions import FastAPIError
from fastapi.testclient import TestClient

from picodi import (
    ContextVarScope,
    Provide,
    dependency,
    init_dependencies,
    inject,
    shutdown_dependencies,
)


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
    async def root(slug_result: dict[str, int] = Depends(get_by_slug)):
        return slug_result

    response = client.get("/", params={"slug": "meaning-of-life"})

    assert response.json() == {"meaning-of-life": 42}


def test_can_use_depends_only_in_view_not_in_nested_deps(app, client):
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


def test_resolve_annotated_dependency(app, client):
    def get_42() -> MyNumber:
        return MyNumber(42)

    @app.get("/")
    @inject
    def root(number: Annotated[MyNumber, Depends(Provide(get_42))]):
        return {"number": number.value}

    response = client.get("/")

    assert response.json() == {"number": 42}


def test_contextvar_scope_can_be_used_as_request_scope(app, client):
    closing_counter = 0

    @app.middleware("http")
    async def manage_request_scoped_deps(request, call_next):
        await init_dependencies(scope_class=ContextVarScope)
        response = await call_next(request)
        await shutdown_dependencies(scope_class=ContextVarScope)
        return response

    @dependency(scope_class=ContextVarScope)
    def get_42():
        yield 42
        nonlocal closing_counter
        closing_counter += 1

    @app.get("/")
    @inject
    def root(
        number1: int = Depends(Provide(get_42)), number2: int = Depends(Provide(get_42))
    ):
        return {"numbers": [number1, number2]}

    response = client.get("/")
    client.get("/")

    assert closing_counter == 2
    assert response.json() == {"numbers": [42, 42]}


async def test_contextvar_scope_can_be_used_as_request_scope_async(app, client):
    closing_counter = 0

    @app.middleware("http")
    async def manage_request_scoped_deps(request, call_next):
        await init_dependencies(scope_class=ContextVarScope)
        response = await call_next(request)
        await shutdown_dependencies(scope_class=ContextVarScope)
        return response

    @dependency(scope_class=ContextVarScope)
    async def get_42():
        yield 42
        nonlocal closing_counter
        closing_counter += 1

    @app.get("/")
    @inject
    async def root(
        number1: int = Depends(Provide(get_42)), number2: int = Depends(Provide(get_42))
    ):
        return {"numbers": [number1, number2]}

    response = client.get("/")
    client.get("/")

    assert closing_counter == 2
    assert response.json() == {"numbers": [42, 42]}
