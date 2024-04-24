from __future__ import annotations

from contextlib import AsyncExitStack
from contextlib import ExitStack as SyncExitStack
from typing import TYPE_CHECKING, Any, AsyncContextManager, ContextManager

if TYPE_CHECKING:
    from collections.abc import Hashable


class Scope:
    def __init__(self) -> None:
        self.exit_stack = ExitStack()

    def get(self, key: Hashable) -> Any:
        raise NotImplementedError

    def set(self, key: Hashable, value: Any) -> None:
        raise NotImplementedError

    def __enter__(self) -> Any:
        return self

    def __exit__(self, *exc_details) -> bool:
        raise NotImplementedError

    async def __aenter__(self) -> Any:
        return self

    async def __aexit__(self, *exc_details) -> None:
        raise NotImplementedError


class GlobalScope(Scope):
    def __exit__(self, *exc_details):
        return None

    async def __aexit__(self, *exc_details) -> None:
        return None


class LocalScope(Scope):
    def __exit__(self, *exc_details):
        return self.exit_stack.__exit__(*exc_details)

    async def __aexit__(self, *exc_details) -> None:
        return await self.exit_stack.__aexit__(*exc_details)


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

    def __enter__(self) -> Any:
        return self

    def __exit__(self, *exc_details) -> bool:
        return self._sync_stack.__exit__(*exc_details)

    async def __aenter__(self) -> Any:
        return self

    async def __aexit__(self, *exc_details) -> None:
        self._sync_stack.__exit__(*exc_details)
        await self._async_stack.__aexit__(*exc_details)

    def enter_context(self, cm, only_sync: bool = False) -> Any:
        if not only_sync and isinstance(cm, AsyncContextManager):
            return self._async_stack.enter_async_context(cm)
        return self._sync_stack.enter_context(cm)

    def close(self, only_sync: bool = False) -> Any:
        self.__exit__(None, None, None)
        if not only_sync:
            return self.__aexit__(None, None, None)
