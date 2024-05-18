from __future__ import annotations

from contextvars import ContextVar
from multiprocessing import RLock
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

    def enter_decorator(self) -> None:
        return None

    def exit_decorator(self) -> None:
        return None


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

    def close_global(self) -> Awaitable:
        self._store.clear()
        return super().close_global()


class CallScope(Scope):
    def __init__(self) -> None:
        super().__init__()
        self._store: dict[Hashable, Any] = {}
        self._lock = RLock()
        self._in_decorator_count = ContextVar("picodi_in_decorator_count", default=0)

    def enter_decorator(self) -> None:
        with self._lock:
            self._in_decorator_count.set(self._in_decorator_count.get() + 1)

    def exit_decorator(self) -> None:
        with self._lock:
            self._in_decorator_count.set(self._in_decorator_count.get() - 1)
            if self._in_decorator_count.get() == 0:
                self._store.clear()
                self.exit_stack.close()

    def get(self, key: Hashable) -> Any:
        try:
            return self._store[key].get()
        except LookupError:
            raise KeyError(key) from None

    def set(self, key: Hashable, value: Any) -> None:
        try:
            var = self._store[key]
        except KeyError:
            var = self._store[key] = ContextVar("picodi")
        var.set(value)
