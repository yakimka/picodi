from typing import Annotated

import pytest
from fastapi import Depends, FastAPI
from fastapi.exceptions import FastAPIError
from starlette.middleware import Middleware

from picodi import (
    InitDependencies,
    SingletonScope,
    dependency,
    inject,
    registry,
    shutdown_dependencies,
)
from picodi.integrations.fastapi import Provide, RequestScope, RequestScopeMiddleware


@pytest.fixture()
def make_app():
    def maker(dependencies_for_init: InitDependencies | None = None):
        kwargs = {}
        if dependencies_for_init:
            kwargs["dependencies_for_init"] = dependencies_for_init
        return FastAPI(
            middleware=[Middleware(RequestScopeMiddleware, **kwargs)],
        )

    return maker


class MyNumber:
    def __init__(self, number: int):
        self.value = number


def test_fastapi_cant_use_provide_as_is(make_app):
    app = make_app()

    def get_42() -> MyNumber:
        return MyNumber(42)  # pragma: no cover

    with pytest.raises(FastAPIError, match="Invalid args for response field"):

        @app.get("/")  # pragma: no cover
        @inject
        async def root(number: MyNumber = Provide(get_42)):
            return {"number": number}  # pragma: no cover


async def test_resolve_dependency_in_route(make_app, make_asgi_client):
    app = make_app()

    def get_42() -> MyNumber:
        return MyNumber(42)

    @app.get("/")
    @inject
    def root(number: MyNumber = Depends(Provide(get_42))):
        return {"number": number.value}

    async with make_asgi_client(app) as asgi_client:
        response = await asgi_client.get("/")

    assert response.json() == {"number": 42}


async def test_resolve_dependency_in_route_only_with_provide(
    make_app, make_asgi_client
):
    app = make_app()

    def get_42() -> MyNumber:
        return MyNumber(42)

    @app.get("/")
    @inject
    def root(number: MyNumber = Provide(get_42, wrap=True)):
        return {"number": number.value}

    async with make_asgi_client(app) as asgi_client:
        response = await asgi_client.get("/")

    assert response.json() == {"number": 42}


async def test_resolve_dependency_in_route_without_inject_decorator(
    make_app, make_asgi_client
):
    app = make_app()

    def get_42() -> MyNumber:
        return MyNumber(42)

    @app.get("/")
    def root(number: MyNumber = Provide(get_42, wrap=True)):
        return {"number": number.value}

    async with make_asgi_client(app) as asgi_client:
        response = await asgi_client.get("/")

    assert response.json() == {"number": 42}


async def test_can_override_deps_passed_to_fastapi_view_without_inject_decorator(
    make_app, make_asgi_client
):
    app = make_app()

    def get_42() -> MyNumber:
        return MyNumber(42)

    @app.get("/")
    def root(number: MyNumber = Provide(get_42, wrap=True)):
        return {"number": number.value}

    with registry.override(get_42, lambda: MyNumber(24)):
        async with make_asgi_client(app) as asgi_client:
            response = await asgi_client.get("/")

    assert response.json() == {"number": 24}


async def test_dependency_scope_close_only_after_view_is_exited(
    make_app, make_asgi_client
):
    app = make_app()
    closed = 0

    def get_42():
        yield MyNumber(42)
        nonlocal closed
        closed += 1

    @app.get("/")
    def root(number: MyNumber = Provide(get_42, wrap=True)):
        assert closed == 0
        return {"number": number.value}

    async with make_asgi_client(app) as asgi_client:
        response = await asgi_client.get("/")

    assert closed == 1
    assert response.json() == {"number": 42}


async def test_singleton_dependency_scope_not_closed_after_view_is_exited(
    make_app, make_asgi_client
):
    app = make_app()
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

    async with make_asgi_client(app) as asgi_client:
        response = await asgi_client.get("/")

    assert closed == 0
    await shutdown_dependencies()
    assert closed == 1
    assert response.json() == {"number": 42}


async def test_resolve_dependency_in_route_async(make_app, make_asgi_client):
    app = make_app()

    async def get_42() -> MyNumber:
        return MyNumber(42)

    @app.get("/")
    @inject
    async def root(number: MyNumber = Depends(Provide(get_42))):
        return {"number": number.value}

    async with make_asgi_client(app) as asgi_client:
        response = await asgi_client.get("/")

    assert response.json() == {"number": 42}


async def test_resolve_mixed_dependency_in_route(make_app, make_asgi_client):
    app = make_app()

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

    async with make_asgi_client(app) as asgi_client:
        response = await asgi_client.get("/", params={"slug": "meaning-of-life"})

    assert response.json() == {"meaning-of-life": 42}


async def test_can_use_provide_in_nested_deps_without_depends(
    make_app, make_asgi_client
):
    app = make_app()

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

    async with make_asgi_client(app) as asgi_client:
        response = await asgi_client.get("/")

    assert response.json() == {"nested": "42"}


async def test_resolve_annotated_dependency(make_app, make_asgi_client):
    app = make_app()

    def get_42() -> MyNumber:
        return MyNumber(42)

    @app.get("/")
    @inject
    def root(number: Annotated[MyNumber, Depends(Provide(get_42))]):
        return {"number": number.value}

    async with make_asgi_client(app) as asgi_client:
        response = await asgi_client.get("/")

    assert response.json() == {"number": 42}


async def test_middleware_init_and_shutdown_request_scope(make_app, make_asgi_client):
    init_counter = 0
    closing_counter = 0

    @dependency(scope_class=RequestScope)
    async def get_42():
        nonlocal init_counter
        init_counter += 1
        yield 42
        nonlocal closing_counter
        closing_counter += 1

    app = make_app([get_42])

    @app.get("/")
    @inject
    async def root():
        assert init_counter == 1
        assert closing_counter == 0
        return {}

    async with make_asgi_client(app) as asgi_client:
        await asgi_client.get("/")

    assert init_counter == 1
    assert closing_counter == 1


async def test_middleware_init_and_shutdown_request_scope_sync(
    make_app, make_asgi_client
):
    init_counter = 0
    closing_counter = 0

    @dependency(scope_class=RequestScope)
    def get_42():
        nonlocal init_counter
        init_counter += 1
        yield 42
        nonlocal closing_counter
        closing_counter += 1

    app = make_app([get_42])

    @app.get("/")
    @inject
    def root():
        assert init_counter == 1
        assert closing_counter == 0
        return {}

    async with make_asgi_client(app) as asgi_client:
        await asgi_client.get("/")

    assert init_counter == 1
    assert closing_counter == 1
