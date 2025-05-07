"""
Support module for picodi package.

May be useful for writing your own scopes or other customizations.
"""

from __future__ import annotations

import asyncio
import inspect
from contextlib import AsyncExitStack
from contextlib import ExitStack as SyncExitStack
from typing import TYPE_CHECKING, Any, AsyncContextManager, ContextManager

if TYPE_CHECKING:
    from collections.abc import Awaitable, Generator
    from types import TracebackType


class NullAwaitable:
    """Dummy awaitable that does nothing."""

    def __await__(self) -> Generator[None]:
        yield
        return None


class ExitStack:
    """
    A context manager that combines multiple context managers - both sync and async.

    Under the hood, it uses :class:`python:contextlib.ExitStack`
    for sync context managers and :class:`python:contextlib.AsyncExitStack` for async
    """

    def __init__(self) -> None:
        self._sync_stack = SyncExitStack()
        self._async_stack = AsyncExitStack()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        return self._sync_stack.__exit__(exc_type, exc, traceback)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        res_sync = self._sync_stack.__exit__(exc_type, exc, traceback)
        res_async = await self._async_stack.__aexit__(exc_type, exc, traceback)
        return res_sync and res_async

    def enter_context(self, cm: AsyncContextManager | ContextManager) -> Any:
        """
        Enters a new context manager and adds its ``__[a]exit__()``
        method to the callback stack.
        The return value is the result of the context manager’s
        own ``__[a]enter__()`` method.

        :param cm: context manager to enter.
        :return: Result of the context manager's ``__[a]enter__`` method.
        """
        if isinstance(cm, ContextManager):
            return self._sync_stack.enter_context(cm)
        elif isinstance(cm, AsyncContextManager):
            return self._async_stack.enter_async_context(cm)

        raise TypeError(f"Unsupported context manager: {cm}")  # pragma: no cover

    def close(self, exc: BaseException | None = None) -> Awaitable:
        """
        Immediately unwinds the callback stack,
        invoking callbacks in the reverse order of registration.

        :param exc: exception to be passed to the ``__[a]exit__`` method.
        """
        exc_type = type(exc) if exc is not None else None
        self.__exit__(exc_type, exc, exc.__traceback__ if exc else None)
        if (
            is_async_environment()
            # This is a workaround for the issue for RuntimeWarning
            # "coroutine was never awaited". If we in sync function in async context -
            # don't need to await for async exit if there are no async context managers.
            and self._async_stack._exit_callbacks  # type: ignore # noqa: SF01
        ):
            return self.__aexit__(exc_type, exc, None)
        return NullAwaitable()


def is_async_environment() -> bool:
    """
    Check if we are in async environment.

    :return: True if we are in async environment, False otherwise.
    """
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return False
    return True


def is_async_function(fn: Any) -> bool:
    """
    Check if the function is async.

    :param fn: function to check.
    :return: True if the function is async, False otherwise.
    """
    if asyncio.iscoroutinefunction(fn) or inspect.isasyncgenfunction(fn):
        return True

    if wrpd := getattr(fn, "__wrapped__", None):
        return is_async_function(wrpd)
    return False
