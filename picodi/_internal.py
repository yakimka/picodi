from __future__ import annotations

import asyncio
from contextlib import AsyncExitStack
from contextlib import ExitStack as SyncExitStack
from typing import TYPE_CHECKING, Any, AsyncContextManager, ContextManager

if TYPE_CHECKING:
    from collections.abc import Awaitable, Generator
    from types import TracebackType


class DummyAwaitable:
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

    def close(self) -> Awaitable:
        self.__exit__(None, None, None)
        if is_async_environment():
            return self.__aexit__(None, None, None)
        return DummyAwaitable()


def is_async_environment() -> bool:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return False
    return True
