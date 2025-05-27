from __future__ import annotations

import threading
from contextvars import ContextVar, Token
from typing import TYPE_CHECKING, Any, AsyncContextManager, ContextManager

import picodi
from picodi.support import ExitStack

if TYPE_CHECKING:
    from collections.abc import Awaitable, Hashable

    from starlette.types import ASGIApp, Receive, Scope, Send


_context: ContextVar[dict[str, Any]] = ContextVar("picodi_starlette_context")
_lock = threading.Lock()


def _get_or_create_context() -> dict[str, Any]:
    try:
        return _context.get()
    except LookupError:
        with _lock:
            # Double check if context was created by another thread
            try:
                return _context.get()
            except LookupError:
                return _new_context()[0]


def _new_context() -> tuple[dict[str, Any], Token]:
    context = {
        "store": {},
        "exit_stack": ExitStack(),
    }
    return context, _context.set(context)


class RequestScope(picodi.ContextVarScope):
    def get(self, key: Hashable, *, global_key: Hashable) -> Any:  # noqa: U100
        context = _get_or_create_context()

        try:
            value = context["store"][key]
        except LookupError:
            raise KeyError(key) from None
        return value

    def set(
        self,
        key: Hashable,
        value: Any,
        *,
        global_key: Hashable,  # noqa: U100
    ) -> None:
        context = _get_or_create_context()
        context["store"][key] = value

    def enter(
        self,
        context_manager: AsyncContextManager | ContextManager,
        *,
        global_key: Hashable,  # noqa: U100
    ) -> Awaitable:
        context = _get_or_create_context()
        exit_stack = context["exit_stack"]
        return exit_stack.enter_context(context_manager)

    def shutdown(
        self, exc: BaseException | None = None, *, global_key: Hashable  # noqa: U100
    ) -> Any:
        context = _get_or_create_context()
        context["store"].clear()
        exit_stack = context["exit_stack"]
        return exit_stack.close(exc)


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

        # initialize context in middleware contextvars
        #   this is needed to ensure that context is available and if starlette
        #   will execute view in another thread and copy contextvars - it will
        #   already have our context
        _, token = _new_context()
        if self._dependencies_for_init:
            await self._registry.init(self._dependencies_for_init)
        try:
            await self.app(scope, receive, send)
        finally:
            await self._registry.shutdown(scope_class=RequestScope)
            _context.reset(token)
