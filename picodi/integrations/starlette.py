from __future__ import annotations

from typing import TYPE_CHECKING

import picodi

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Receive, Scope, Send


class RequestScope(picodi.ContextVarScope):
    """
    Request scope. Values cached in contextvars.
    Dependencies initialized on request start and closed on request end.
    """


class RequestScopeMiddleware:
    """
    Starlette Pure ASGI Middleware for automatically
    initializing and closing request scoped dependencies
    """

    def __init__(self, app: ASGIApp, context: picodi.Context | None = None) -> None:
        self.app = app
        self._context = context

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if self._context:
            await self._context.init_dependencies()
        try:
            await self.app(scope, receive, send)
        finally:
            if self._context:
                await self._context.shutdown_dependencies(  # noqa: ASYNC102
                    scope_class=RequestScope
                )
