from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from starlette.applications import Starlette
from starlette.middleware import Middleware
from starlette.requests import Request
from starlette.responses import PlainTextResponse
from starlette.routing import Route

from picodi.integrations.starlette import RequestScope, RequestScopeMiddleware

if TYPE_CHECKING:
    from picodi import Context


@pytest.fixture()
def make_app():
    def maker(context: Context):
        def sync_view(request: Request) -> PlainTextResponse:  # noqa: U100
            return PlainTextResponse("sync view")

        async def async_view(request: Request) -> PlainTextResponse:  # noqa: U100
            return PlainTextResponse("async view")

        return Starlette(
            routes=[Route("/sync-view", sync_view), Route("/async-view", async_view)],
            middleware=[Middleware(RequestScopeMiddleware, context=context)],
        )

    return maker


async def test_middleware_init_and_shutdown_request_scope(
    make_app, make_asgi_client, make_context
):
    init_counter = 0
    closing_counter = 0

    async def get_42():
        nonlocal init_counter
        init_counter += 1
        yield 42
        nonlocal closing_counter
        closing_counter += 1

    context = make_context((get_42, RequestScope), init_dependencies=[get_42])
    app = make_app(context=context)

    async with context:
        async with make_asgi_client(app) as asgi_client:
            await asgi_client.get("/async-view")

    assert init_counter == 1
    assert closing_counter == 1


async def test_middleware_init_and_shutdown_request_scope_sync(
    make_app, make_asgi_client, make_context
):
    init_counter = 0
    closing_counter = 0

    def get_42():
        nonlocal init_counter
        init_counter += 1
        yield 42
        nonlocal closing_counter
        closing_counter += 1

    context = make_context((get_42, RequestScope), init_dependencies=[get_42])
    app = make_app(context=context)

    async with context:
        async with make_asgi_client(app) as asgi_client:
            await asgi_client.get("/sync-view")

    assert init_counter == 1
    assert closing_counter == 1
