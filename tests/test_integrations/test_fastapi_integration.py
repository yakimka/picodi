from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.exceptions import FastAPIError
from starlette.middleware import Middleware

from picodi import SingletonScope, dependency, inject, registry, shutdown_dependencies
from picodi.integrations.fastapi import Provide, RequestScope, RequestScopeMiddleware


@pytest.fixture()
def app():
    return FastAPI(
        middleware=[Middleware(RequestScopeMiddleware)],
    )


class MyNumber:
    def __init__(self, number: int):
        self.value = number


def test_fastapi_cant_use_provide_as_is(app):
    def get_42() -> MyNumber:
        return MyNumber(42)  # pragma: no cover

    with pytest.raises(FastAPIError, match="Invalid args for response field"):

        @app.get("/")  # pragma: no cover
        @inject
        async def root(number: MyNumber = Provide(get_42)):
            return {"number": number}  # pragma: no cover


async def test_resolve_dependency_in_route(app, asgi_client):
    def get_42() -> MyNumber:
        return MyNumber(42)

    @app.get("/")
    @inject
    def root(number: MyNumber = Depends(Provide(get_42))):
        return {"number": number.value}

    response = await asgi_client.get("/")

    assert response.json() == {"number": 42}


async def test_resolve_dependency_in_route_only_with_provide(app, asgi_client):
    def get_42() -> MyNumber:
        return MyNumber(42)

    @app.get("/")
    @inject
    def root(number: MyNumber = Provide(get_42, wrap=True)):
        return {"number": number.value}

    response = await asgi_client.get("/")

    assert response.json() == {"number": 42}


async def test_resolve_dependency_in_route_without_inject_decorator(app, asgi_client):
    def get_42() -> MyNumber:
        return MyNumber(42)

    @app.get("/")
    def root(number: MyNumber = Provide(get_42, wrap=True)):
        return {"number": number.value}

    response = await asgi_client.get("/")

    assert response.json() == {"number": 42}


async def test_can_override_deps_passed_to_fastapi_view_without_inject_decorator(
    app, asgi_client
):
    def get_42() -> MyNumber:
        return MyNumber(42)

    @app.get("/")
    def root(number: MyNumber = Provide(get_42, wrap=True)):
        return {"number": number.value}

    with registry.override(get_42, lambda: MyNumber(24)):
        response = await asgi_client.get("/")

    assert response.json() == {"number": 24}


async def test_dependency_scope_close_only_after_view_is_exited(app, asgi_client):
    closed = 0

    def get_42():
        yield MyNumber(42)
        nonlocal closed
        closed += 1

    @app.get("/")
    def root(number: MyNumber = Provide(get_42, wrap=True)):
        assert closed == 0
        return {"number": number.value}

    response = await asgi_client.get("/")

    assert closed == 1
    assert response.json() == {"number": 42}


async def test_singleton_dependency_scope_not_closed_after_view_is_exited(
    app, asgi_client
):
    closed = 0

    @dependency(scope_class=SingletonScope)
    def get_42():
        yield MyNumber(42)
        nonlocal closed
        closed += 1

    @app.get("/")
    def root(number: MyNumber = Provide(get_42, wrap=True)):
        assert closed == 0
        return {"number": number.value}

    response = await asgi_client.get("/")

    assert closed == 0
    await shutdown_dependencies()
    assert closed == 1
    assert response.json() == {"number": 42}


async def test_resolve_dependency_in_route_async(app, asgi_client):
    async def get_42() -> MyNumber:
        return MyNumber(42)

    @app.get("/")
    @inject
    async def root(number: MyNumber = Depends(Provide(get_42))):
        return {"number": number.value}

    response = await asgi_client.get("/")

    assert response.json() == {"number": 42}


async def test_resolve_mixed_dependency_in_route(app, asgi_client):
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

    response = await asgi_client.get("/", params={"slug": "meaning-of-life"})

    assert response.json() == {"meaning-of-life": 42}


async def test_can_use_provide_in_nested_deps_without_depends(app, asgi_client):
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

    response = await asgi_client.get("/")

    assert response.json() == {"nested": "42"}


async def test_resolve_annotated_dependency(app, asgi_client):
    def get_42() -> MyNumber:
        return MyNumber(42)

    @app.get("/")
    @inject
    def root(number: Annotated[MyNumber, Depends(Provide(get_42))]):
        return {"number": number.value}

    response = await asgi_client.get("/")

    assert response.json() == {"number": 42}


async def test_middleware_init_and_shutdown_request_scope(app, asgi_client):
    init_counter = 0
    closing_counter = 0

    @dependency(scope_class=RequestScope, use_init_hook=True)
    async def get_42():
        nonlocal init_counter
        init_counter += 1
        yield 42
        nonlocal closing_counter
        closing_counter += 1

    @app.get("/")
    @inject
    async def root():
        assert init_counter == 1
        assert closing_counter == 0
        return {}

    await asgi_client.get("/")

    assert init_counter == 1
    assert closing_counter == 1


async def test_middleware_init_and_shutdown_request_scope_sync(app, asgi_client):
    init_counter = 0
    closing_counter = 0

    @dependency(scope_class=RequestScope, use_init_hook=True)
    def get_42():
        nonlocal init_counter
        init_counter += 1
        yield 42
        nonlocal closing_counter
        closing_counter += 1

    @app.get("/")
    @inject
    def root():
        assert init_counter == 1
        assert closing_counter == 0
        return {}

    await asgi_client.get("/")

    assert init_counter == 1
    assert closing_counter == 1
