from __future__ import annotations

from contextvars import ContextVar
from typing import TYPE_CHECKING, Any

from picodi._internal import ExitStack, NullAwaitable

if TYPE_CHECKING:
    from collections.abc import Awaitable, Hashable


unset = object()


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

    def shutdown_auto(
        self, exc: BaseException | None = None  # noqa: U100
    ) -> Awaitable:
        """
        Hook for closing dependencies. Will be called automatically
        after executing a decorated function.
        """
        return NullAwaitable()

    def shutdown(self, exc: BaseException | None = None) -> Awaitable:  # noqa: U100
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
        `shutdown_auto` will be called after this, e.g.:
            `exit_inject` -> `shutdown_auto` -> `inject` wrapper returns.
        """
        return None


class ManualScope(Scope):
    """
    Inherit this class for your custom scope that you need to clear automatically.
    """

    def shutdown(self, exc: BaseException | None = None) -> Awaitable:
        return self.exit_stack.close(exc)


class AutoScope(Scope):
    """
    Inherit this class for your custom scope.
    """

    def shutdown(self, exc: BaseException | None = None) -> Awaitable:
        return self.exit_stack.close(exc)

    def shutdown_auto(self, exc: BaseException | None = None) -> Awaitable:
        return self.shutdown(exc)


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

    def shutdown(self, exc: BaseException | None = None) -> Awaitable:
        self._store.clear()
        return super().shutdown(exc)


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
            value = self._store[key].get()
        except LookupError:
            raise KeyError(key) from None
        if value is unset:
            raise KeyError(key)
        return value

    def set(self, key: Hashable, value: Any) -> None:
        try:
            var = self._store[key]
        except KeyError:
            var = self._store[key] = ContextVar("picodi_FastApiScope_var")
        var.set(value)

    def shutdown(self, exc: BaseException | None = None) -> Any:
        for var in self._store.values():
            var.set(unset)
        return super().shutdown(exc)
