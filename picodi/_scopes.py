from __future__ import annotations

from contextvars import ContextVar
from typing import TYPE_CHECKING, Any

from picodi._internal import ExitStack, NullAwaitable

if TYPE_CHECKING:
    from collections.abc import Awaitable, Hashable


class Scope:
    """
    Base class for scopes.

    Scopes are used to store and retrieve values by key and for closing dependencies.
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

    def close_local(self, exc: BaseException | None = None) -> Awaitable:  # noqa: U100
        """
        Hook for closing dependencies. Will be called automatically
        after executing a decorated function.
        """
        return NullAwaitable()

    def close_global(self, exc: BaseException | None = None) -> Awaitable:  # noqa: U100
        """
        Hook for closing dependencies. Will be called from `shutdown_dependencies`.
        """
        return NullAwaitable()

    def enter_inject(self) -> None:
        """
        Called when entering a `inject` decorator.
        """
        return None

    def exit_inject(self, exc: BaseException | None = None) -> None:  # noqa: U100
        """
        Called before exiting a `inject` decorator.
        `close_local` will be called after this, e.g.:
            `exit_inject` -> `close_local` -> `inject` wrapper returns.
        """
        return None


class ManualScope(Scope):
    """
    Inherit this class for your custom global scope.
    """

    def close_global(self, exc: BaseException | None = None) -> Awaitable:
        return self.exit_stack.close(exc)


class AutoScope(Scope):
    """
    Inherit this class for your custom local scope.
    """

    def close_local(self, exc: BaseException | None = None) -> Awaitable:
        return self.exit_stack.close(exc)

    def close_global(self, exc: BaseException | None = None) -> Awaitable:
        return self.exit_stack.close(exc)


class NullScope(AutoScope):
    """
    Null scope. Values not cached, dependencies closed after every function call.
    """

    def get(self, key: Hashable) -> Any:
        raise KeyError(key)

    def set(self, key: Hashable, value: Any) -> None:  # noqa: U100
        return None


class SingletonScope(ManualScope):
    """
    Singleton scope. Values cached for the lifetime of the application.
    Dependencies closed only when user manually call `shutdown_dependencies`.
    """

    def __init__(self) -> None:
        super().__init__()
        self._store: dict[Hashable, Any] = {}

    def get(self, key: Hashable) -> Any:
        return self._store[key]

    def set(self, key: Hashable, value: Any) -> None:
        self._store[key] = value

    def close_global(self, exc: BaseException | None = None) -> Awaitable:
        self._store.clear()
        return super().close_global(exc)


class ContextVarScope(ManualScope):
    """
    ContextVar scope. Values cached in contextvars.
    Dependencies closed only when user manually call `shutdown_dependencies`.
    """

    def __init__(self) -> None:
        super().__init__()
        self._store: dict[Any, ContextVar[Any]] = {}

    def get(self, key: Hashable) -> Any:
        try:
            return self._store[key].get()
        except LookupError:
            raise KeyError(key) from None

    def set(self, key: Hashable, value: Any) -> None:
        try:
            var = self._store[key]
        except KeyError:
            var = self._store[key] = ContextVar("picodi_FastApiScope_var")
        var.set(value)

    def close_global(self, exc: BaseException | None = None) -> Any:
        for var in self._store.values():
            var.set(None)
        self._store.clear()
        return super().close_global(exc)
