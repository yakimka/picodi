from __future__ import annotations

from typing import TYPE_CHECKING, Any

from picodi._internal import DummyAwaitable, ExitStack

if TYPE_CHECKING:
    from collections.abc import Awaitable, Hashable


class Scope:
    def __init__(self) -> None:
        self.exit_stack = ExitStack()

    def get(self, key: Hashable) -> Any:
        raise NotImplementedError

    def set(self, key: Hashable, value: Any) -> None:
        raise NotImplementedError

    def close_local(self) -> Awaitable:
        return DummyAwaitable()

    def close_global(self) -> Awaitable:
        return DummyAwaitable()


class GlobalScope(Scope):
    def close_global(self) -> Awaitable:
        return self.exit_stack.close()


class LocalScope(Scope):
    def close_local(self) -> Awaitable:
        return self.exit_stack.close()


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
