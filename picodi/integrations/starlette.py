from __future__ import annotations

from typing import TYPE_CHECKING

import picodi

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send


class RequestScope(picodi.ContextVarScope):
    pass


class PicodiRequestScopeMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def send_wrapper(message: Message) -> None:
            await picodi.init_dependencies(scope_class=RequestScope)
            await send(message)
            await picodi.shutdown_dependencies(scope_class=RequestScope)

        await self.app(scope, receive, send_wrapper)
