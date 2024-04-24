from __future__ import annotations

from contextlib import AsyncExitStack
from contextlib import ExitStack as SyncExitStack
from typing import TYPE_CHECKING, Any, AsyncContextManager, ContextManager

if TYPE_CHECKING:
    from collections.abc import Awaitable, Hashable
    from types import TracebackType


class Scope:
    def __init__(self) -> None:
        self.exit_stack = ExitStack()

    def get(self, key: Hashable) -> Any:
        raise NotImplementedError

    def set(self, key: Hashable, value: Any) -> None:
        raise NotImplementedError

    def __enter__(self) -> Any:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        raise NotImplementedError

    async def __aenter__(self) -> Scope:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        raise NotImplementedError


class GlobalScope(Scope):
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        return None

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        return None


class LocalScope(Scope):
    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        return self.exit_stack.__exit__(exc_type, exc, traceback)

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        return await self.exit_stack.__aexit__(exc_type, exc, traceback)


class NullScope(LocalScope):
    def get(self, key: Hashable) -> Any:
        raise KeyError(key)

    def set(self, key: Hashable, value: Any) -> None:
        pass


class SingletonScope(GlobalScope):
    def __init__(self) -> None:
        super().__init__()
        self._store: dict[Hashable, Any] = {}

    def get(self, key: Hashable) -> Any:
        return self._store[key]

    def set(self, key: Hashable, value: Any) -> None:
        self._store[key] = value


class ExitStack:
    def __init__(self) -> None:
        self._sync_stack = SyncExitStack()
        self._async_stack = AsyncExitStack()

    def __enter__(self) -> ExitStack:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        return self._sync_stack.__exit__(exc_type, exc, traceback)

    async def __aenter__(self) -> ExitStack:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> bool | None:
        res_sync = self._sync_stack.__exit__(exc_type, exc, traceback)
        res_async = await self._async_stack.__aexit__(exc_type, exc, traceback)
        return res_sync and res_async

    def enter_context(
        self, cm: AsyncContextManager | ContextManager, sync_first: bool = False
    ) -> Any:
        if isinstance(cm, ContextManager) and isinstance(cm, AsyncContextManager):
            if sync_first:
                return self._sync_stack.enter_context(cm)
            else:
                return self._async_stack.enter_async_context(cm)
        if isinstance(cm, ContextManager):
            return self._sync_stack.enter_context(cm)
        elif isinstance(cm, AsyncContextManager):
            return self._async_stack.enter_async_context(cm)

    def close(self, only_sync: bool = False) -> Awaitable | None:
        self.__exit__(None, None, None)
        if not only_sync:
            return self.__aexit__(None, None, None)
        return None
