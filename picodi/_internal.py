from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
from contextlib import ExitStack as SyncExitStack
from typing import TYPE_CHECKING, Any, AsyncContextManager, ContextManager

if TYPE_CHECKING:
    from collections.abc import Awaitable, Generator
    from types import TracebackType


class NullAwaitable:
    def __await__(self) -> Generator[None, None, None]:
        yield
        return None


class ExitStack:
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
        if isinstance(cm, ContextManager):
            return self._sync_stack.enter_context(cm)
        elif isinstance(cm, AsyncContextManager):
            return self._async_stack.enter_async_context(cm)

        raise TypeError(f"Unsupported context manager: {cm}")  # pragma: no cover

    def close(self, exc: BaseException | None = None) -> Awaitable:
        exc_type = type(exc) if exc is not None else None
        self.__exit__(exc_type, exc, None)
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
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return False
    return True
