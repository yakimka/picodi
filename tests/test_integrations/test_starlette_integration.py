import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from picodi import dependency
from picodi.integrations.starlette import PicodiRequestScopeMiddleware, RequestScope


@pytest.fixture()
def app():
    def sync_view(request: Request) -> PlainTextResponse:  # noqa: U100
        return PlainTextResponse("sync view")

    async def async_view(request: Request) -> PlainTextResponse:  # noqa: U100
        return PlainTextResponse("async view")

    return Starlette(
        routes=[Route("/sync-view", sync_view), Route("/async-view", async_view)],
        middleware=[Middleware(PicodiRequestScopeMiddleware)],
    )


async def test_middleware_init_and_shutdown_request_scope(asgi_client):
    init_counter = 0
    closing_counter = 0

    @dependency(scope_class=RequestScope)
    async def get_42():
        nonlocal init_counter
        init_counter += 1
        yield 42
        nonlocal closing_counter
        closing_counter += 1

    await asgi_client.get("/async-view")

    assert init_counter == 1
    assert closing_counter == 1


async def test_middleware_init_and_shutdown_request_scope_sync(asgi_client):
    init_counter = 0
    closing_counter = 0

    @dependency(scope_class=RequestScope)
    def get_42():
        nonlocal init_counter
        init_counter += 1
        yield 42
        nonlocal closing_counter
        closing_counter += 1

    await asgi_client.get("/sync-view")

    assert init_counter == 1
    assert closing_counter == 1
