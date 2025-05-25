import asyncio

import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse
from starlette.routing import Route

from picodi import InitDependencies, Provide, inject, registry
from picodi.integrations.starlette import RequestScope, RequestScopeMiddleware


@pytest.fixture()
def make_app():
    def maker(
        dependencies_for_init: InitDependencies | None = None,
        routes: list[Route] | None = None,
    ):
        if routes is None:

            def sync_view(request: Request) -> PlainTextResponse:  # noqa: U100
                return PlainTextResponse("sync view")

            async def async_view(request: Request) -> PlainTextResponse:  # noqa: U100
                return PlainTextResponse("async view")

            routes = [
                Route("/sync-view", sync_view),
                Route("/async-view", async_view),
            ]

        return Starlette(
            routes=routes,
            middleware=[
                Middleware(
                    RequestScopeMiddleware, dependencies_for_init=dependencies_for_init
                )
            ],
        )

    return maker


async def test_middleware_init_and_shutdown_request_scope(make_app, make_asgi_client):
    init_counter = 0
    closing_counter = 0

    @registry.set_scope(RequestScope)
    async def get_42():
        nonlocal init_counter
        init_counter += 1
        yield 42
        nonlocal closing_counter
        closing_counter += 1

    app = make_app([get_42])

    async with make_asgi_client(app) as asgi_client:
        await asgi_client.get("/async-view")

    assert init_counter == 1
    assert closing_counter == 1


async def test_middleware_init_and_shutdown_request_scope_sync(
    make_app, make_asgi_client
):
    init_counter = 0
    closing_counter = 0

    @registry.set_scope(RequestScope)
    def get_42():
        nonlocal init_counter
        init_counter += 1
        yield 42
        nonlocal closing_counter
        closing_counter += 1

    app = make_app([get_42])

    async with make_asgi_client(app) as asgi_client:
        await asgi_client.get("/sync-view")

    assert init_counter == 1
    assert closing_counter == 1


async def test_can_use_request_scope_dependency_async(make_app, make_asgi_client):
    init_counter = 0
    closing_counter = 0

    @registry.set_scope(RequestScope)
    async def get_42():
        nonlocal init_counter
        init_counter += 1
        yield 42
        nonlocal closing_counter
        closing_counter += 1

    @inject
    async def root(request: Request, dep: int = Provide(get_42)):
        return JSONResponse({"dep": dep})

    app = make_app(routes=[Route("/", root)])

    async with make_asgi_client(app) as asgi_client:
        await asyncio.gather(
            asgi_client.get("/"),
            asgi_client.get("/"),
            asgi_client.get("/"),
            asgi_client.get("/"),
        )
        resp = await asgi_client.get("/")

    assert resp.json() == {"dep": 42}
    assert init_counter == 5
    assert closing_counter == 5


async def test_can_use_request_scope_dependency_sync(make_app, make_asgi_client):
    init_counter = 0
    closing_counter = 0

    @registry.set_scope(RequestScope)
    def get_42():
        nonlocal init_counter
        init_counter += 1
        yield 42
        nonlocal closing_counter
        closing_counter += 1

    @inject
    def root(request: Request, dep: int = Provide(get_42)):
        return JSONResponse({"dep": dep})

    app = make_app(routes=[Route("/", root)])

    async with make_asgi_client(app) as asgi_client:
        await asyncio.gather(
            asgi_client.get("/"),
            asgi_client.get("/"),
            asgi_client.get("/"),
            asgi_client.get("/"),
        )
        resp = await asgi_client.get("/")

    assert resp.json() == {"dep": 42}
    assert init_counter == 5
    assert closing_counter == 5
