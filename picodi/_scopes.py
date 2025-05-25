from __future__ import annotations

from contextvars import ContextVar
from typing import TYPE_CHECKING, Any, AsyncContextManager, ContextManager, TypeAlias

from picodi.support import ExitStack, NullAwaitable

if TYPE_CHECKING:
    from collections.abc import Awaitable, Hashable


unset = object()


class Scope:
    """
    Scopes are used to store and retrieve values by key and for closing dependencies.

    Don't use this class directly and don't inherit from it.
    Inherit from :class:`AutoScope` or :class:`ManualScope`.
    """

    def get(self, key: Hashable, *, global_key: Hashable) -> Any:
        """
        Get a value by key.
        If value is not exists must raise KeyError.

        :param key: key to get value, typically a dependency function.
        :param global_key: typically a function that requesting dependencies
        :raises KeyError: if value not exists.
        """
        raise NotImplementedError

    def set(self, key: Hashable, value: Any, *, global_key: Hashable) -> None:
        """
        Set a value by key.

        :param key: key to set value, typically a dependency function.
        :param value: value to set, typically a dependency instance.
        :param global_key: typically a function that requesting dependencies
        """
        raise NotImplementedError

    def enter_inject(self, global_key: Hashable) -> None:  # noqa: U100
        """
        Called when entering an :func:`inject` decorator.

        :param global_key: typically a function that requesting dependencies
        """
        return None

    def exit_inject(
        self, exc: BaseException | None = None, *, global_key: Hashable  # noqa: U100
    ) -> None:
        """
        Called before exiting a :func:`inject` decorator.

        ``shutdown`` will be called after this, e.g.:
            ``exit_inject`` -> ``shutdown`` -> ``inject`` wrapper returns.

        :param exc: exception that was raised in the context.
        :param global_key: typically a function that requesting dependencies
        """
        return None


class AutoScope(Scope):
    """
    AutoScope is a scope that automatically closes dependencies
    after exiting the context.

    Don't use this class directly.
    """


class ManualScope(Scope):
    """
    ManualScope is a scope that requires manual closing of dependencies.
    For example :class:`SingletonScope` or :class:`ContextVarScope` use this scope.
    You can close dependencies by calling :func:`shutdown_dependencies` or
    ``shutdown_dependencies(scope_class=MyCustomScope)``
    for shutdown only dependencies that uses :class:`MyCustomScope` scope.

    Don't use this class directly.
    Inherit this class for your custom scope.
    """

    def enter(
        self,
        context_manager: AsyncContextManager | ContextManager,  # noqa: U100
        *,
        global_key: Hashable,  # noqa: U100
    ) -> Awaitable:
        """
        Hook for entering yielded dependencies context. Will be called automatically
        by picodi or when you call :func:`init_dependencies`.

        :param context_manager: context manager created from yield dependency.
        :param global_key: typically a function that requesting dependencies
        """
        return NullAwaitable()

    def shutdown(
        self, exc: BaseException | None = None, *, global_key: Hashable  # noqa: U100
    ) -> Awaitable:
        """
        Hook for shutdown dependencies.
        Will be called when you call :func:`shutdown_dependencies`

        :param exc: exception that was raised in the context.
        :param global_key: typically a function that requesting dependencies
        """
        return NullAwaitable()


ScopeType: TypeAlias = AutoScope | ManualScope


class NullScope(AutoScope):
    """
    Null scope.
    Values aren't cached, dependencies closed automatically after function call.
    This is the default scope.
    """

    def get(self, key: Hashable, *, global_key: Hashable) -> Any:  # noqa: U100
        raise KeyError(key)

    def set(
        self, key: Hashable, value: Any, *, global_key: Hashable  # noqa: U100
    ) -> None:
        return None


class SingletonScope(ManualScope):
    """
    Singleton scope. Values cached for the lifetime of the application.
    Dependencies closed only when user manually call :func:`shutdown_dependencies`.
    """

    def __init__(self) -> None:
        self._exit_stack = ExitStack()
        self._store: dict[Hashable, Any] = {}

    def get(self, key: Hashable, *, global_key: Hashable) -> Any:  # noqa: U100
        return self._store[key]

    def set(
        self,
        key: Hashable,
        value: Any,
        *,
        global_key: Hashable,  # noqa: U100
    ) -> None:
        self._store[key] = value

    def enter(
        self,
        context_manager: AsyncContextManager | ContextManager,
        *,
        global_key: Hashable,  # noqa: U100
    ) -> Awaitable:
        return self._exit_stack.enter_context(context_manager)

    def shutdown(
        self, exc: BaseException | None = None, *, global_key: Hashable  # noqa: U100
    ) -> Awaitable:
        self._store.clear()
        return self._exit_stack.close(exc)


class ContextVarScope(ManualScope):
    """
    ContextVar scope. Values cached in contextvars.
    Dependencies closed only when user manually call :func:`shutdown_dependencies`.
    """

    def __init__(self) -> None:
        self._exit_stack: ContextVar[ExitStack] = ContextVar(
            "picodi_ContextVarScope_exit_stack"
        )
        self._store: dict[Any, ContextVar[Any]] = {}

    def get(self, key: Hashable, *, global_key: Hashable) -> Any:  # noqa: U100
        try:
            value = self._store[key].get()
        except LookupError:
            raise KeyError(key) from None
        if value is unset:
            raise KeyError(key)
        return value

    def set(
        self,
        key: Hashable,
        value: Any,
        *,
        global_key: Hashable,  # noqa: U100
    ) -> None:
        try:
            var = self._store[key]
        except KeyError:
            var = self._store[key] = ContextVar("picodi_ContextVarScope_var")
        var.set(value)

    def enter(
        self,
        context_manager: AsyncContextManager | ContextManager,
        *,
        global_key: Hashable,  # noqa: U100
    ) -> Awaitable:
        exit_stack = self._get_exit_stack()
        return exit_stack.enter_context(context_manager)

    def shutdown(
        self, exc: BaseException | None = None, *, global_key: Hashable  # noqa: U100
    ) -> Any:
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
