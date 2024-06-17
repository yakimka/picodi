from __future__ import annotations

from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, AsyncContextManager, ContextManager, TypeAlias

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


class AutoScope(Scope):
    """
    Inherit this class for your custom scope.
    """

    def enter(
        self,
        exit_stack: ExitStack,
        context_manager: AsyncContextManager | ContextManager,
    ) -> Awaitable:
        """
        Hook for entering yielded dependencies context. Will be called automatically
        by picodi.
        Usually you don't need to override this method.
        """
        return exit_stack.enter_context(context_manager)

    def shutdown(
        self, exit_stack: ExitStack, exc: BaseException | None = None
    ) -> Awaitable:
        """
        Hook for closing dependencies. Will be called automatically by picodi.
        Usually you don't need to override this method.
        """
        return exit_stack.close(exc)


class ManualScope(Scope):
    """
    Inherit this class for your custom scope that you need to clear automatically.
    """

    def enter(
        self, context_manager: AsyncContextManager | ContextManager  # noqa: U100
    ) -> Awaitable:
        """
        Hook for entering yielded dependencies context. Will be called automatically
        by picodi or when you call `init_dependencies`.
        """
        return NullAwaitable()

    def shutdown(self, exc: BaseException | None = None) -> Awaitable:  # noqa: U100
        """
        Hook for shutdown dependencies.
        Will be called when you call `shutdown_dependencies`
        """
        return NullAwaitable()


ScopeType: TypeAlias = AutoScope | ManualScope


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
        self._exit_stack = ExitStack()
        self._store: dict[Hashable, Any] = {}

    def get(self, key: Hashable) -> Any:
        return self._store[key]

    def set(self, key: Hashable, value: Any) -> None:
        self._store[key] = value

    def enter(self, context_manager: AsyncContextManager | ContextManager) -> Awaitable:
        return self._exit_stack.enter_context(context_manager)

    def shutdown(self, exc: BaseException | None = None) -> Awaitable:
        self._store.clear()
        return self._exit_stack.close(exc)


class ContextVarScope(ManualScope):
    """
    ContextVar scope. Values cached in contextvars.
    Dependencies closed only when user manually call `shutdown_dependencies`.
    """

    def __init__(self) -> None:
        self._exit_stack: ContextVar[ExitStack] = ContextVar(
            "picodi_ContextVarScope_exit_stack"
        )
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

    def enter(self, context_manager: AsyncContextManager | ContextManager) -> Awaitable:
        exit_stack = self._get_exit_stack()
        return exit_stack.enter_context(context_manager)

    def shutdown(self, exc: BaseException | None = None) -> Any:
        for var in self._store.values():
            var.set(unset)
        exit_stack = self._get_exit_stack()
        return exit_stack.close(exc)

    def _get_exit_stack(self) -> ExitStack:
        try:
            stack = self._exit_stack.get()
        except LookupError:
            stack = ExitStack()
            self._exit_stack.set(stack)
        return stack
