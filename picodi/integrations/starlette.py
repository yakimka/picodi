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

    def __init__(
        self,
        app: ASGIApp,
        *,
        registry: picodi.Registry | None = None,
        dependencies_for_init: picodi.InitDependencies | None = None,
    ) -> None:
        self.app = app
        self._registry = registry or picodi.registry
        self._dependencies_for_init = dependencies_for_init

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        if self._dependencies_for_init:
            await self._registry.init(self._dependencies_for_init)
        try:
            await self.app(scope, receive, send)
        finally:
            await self._registry.shutdown(scope_class=RequestScope)
