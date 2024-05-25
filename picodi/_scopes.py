from __future__ import annotations

from contextvars import ContextVar
from multiprocessing import RLock
from typing import TYPE_CHECKING, Any

from picodi._internal import DummyAwaitable, ExitStack

if TYPE_CHECKING:
    from collections.abc import Awaitable, Hashable


class Scope:
    """
    Base class for scopes.

    Scopes are used to store and retrieve values by key and for closing resources.
    For implementing a custom scope,
    inherit from this class and implement the abstract methods.
    """

    def __init__(self) -> None:
        self.exit_stack = ExitStack()

    def get(self, key: Hashable) -> Any:
        """
        Get a value by key.
        If value is not exists must raise KeyError.
        """
        raise NotImplementedError

    def set(self, key: Hashable, value: Any) -> None:
        """
        Set a value by key.
        """
        raise NotImplementedError

    def close_local(self) -> Awaitable:
        """
        Hook for closing resources. Will be called automatically
        after executing a decorated function.
        """
        return DummyAwaitable()

    def close_global(self) -> Awaitable:
        """
        Hook for closing resources. Will be called from `shutdown_resources`.
        """
        return DummyAwaitable()

    def enter_decorator(self) -> None:
        """
        Called when entering a `inject` decorator.
        """
        return None

    def exit_decorator(self) -> None:
        """
        Called before exiting a `inject` decorator.
        Can be used for tracking the number of decorators.
        """
        return None


class GlobalScope(Scope):
    """
    Inherit this class for your custom global scope.
    """

    def close_global(self) -> Awaitable:
        return self.exit_stack.close()


class LocalScope(Scope):
    """
    Inherit this class for your custom local scope.
    """

    def close_local(self) -> Awaitable:
        return self.exit_stack.close()


class NullScope(LocalScope):
    """
    Null scope. Values not cached, resources closed after every function call.
    """

    def get(self, key: Hashable) -> Any:
        raise KeyError(key)

    def set(self, key: Hashable, value: Any) -> None:
        pass


class SingletonScope(GlobalScope):
    """
    Singleton scope. Values cached for the lifetime of the application.
    Resources closed only when user manually call `shutdown_resources`.
    """

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


class ParentCallScope(Scope):
    """
    ParentCall scope. Values cached for the lifetime of the top function call.
    Resources are closed after top function call executed.
    """

    def __init__(self) -> None:
        super().__init__()
        self._lock = RLock()
        self._stack = ContextVar("picodi_ParentCallScope_stack", default=[])

    def enter_decorator(self) -> None:
        with self._lock:
            self._stack.get().append({})

    def exit_decorator(self) -> None:
        with self._lock:
            self._stack.get().pop()

    def get(self, key: Hashable) -> Any:
        for frame in self._stack.get():
            if key in frame:
                return frame[key]
        raise KeyError(key)

    def set(self, key: Hashable, value: Any) -> None:
        for frame in self._stack.get():
            if key not in frame:
                frame[key] = value
                break
