from __future__ import annotations

import inspect
from typing import TYPE_CHECKING, Any

import picodi
from picodi._picodi import DependencyCallable, Depends

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send


__all__ = [
    "Provide",
    "RequestScope",
    "PicodiRequestScopeMiddleware",
]


class DependsCallable(Depends):
    def __call__(self) -> Any:
        return self


class DependsAsyncCallable(Depends):
    async def __call__(self) -> Any:
        return self


def Provide(dependency: DependencyCallable, /) -> Any:  # noqa: N802
    if inspect.iscoroutinefunction(dependency):
        return DependsAsyncCallable(dependency)
    return DependsCallable(dependency)


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
