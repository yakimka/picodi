"""
Helper functions and classes for picodi.
"""

from __future__ import annotations

import asyncio
import contextlib
import inspect
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncContextManager,
    ContextManager,
    ParamSpec,
    TypeVar,
    overload,
)

import picodi
from picodi import ManualScope, SingletonScope
from picodi._picodi import LifespanScopeClass, _internal_registry
from picodi.support import nullcontext

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable, Coroutine, Generator

sentinel = object()


class PathNotFoundError(Exception):
    def __init__(self, current_path: str, obj: Any):
        self.current_path = current_path
        self.obj = obj
        super().__init__(f"Can't find path '{current_path}' in {type(obj)} object")


def get_value(path: str, obj: Any, *, default: Any = sentinel) -> Any:
    """
    Get attribute from nested objects.
    Can be useful to avoid passing entire objects like
    settings to functions that only need a small part of it.

    :param path: path to the attribute, separated by dots.
    :param obj: object to search the attribute in.
    :param default: default value to return if the attribute is not found.
        If not provided, an :exc:`PathNotFoundError` is raised.

    :raises PathNotFoundError: if the path is not found in the object
        and default is not provided.

    Example
    -------
    .. code-block:: python

        obj = SimpleNamespace(foo=SimpleNamespace(bar={"baz": 42}))

        get_value("foo.bar.baz", obj)  # Output: 42
        get_value("foo.bar.baz2", obj)  # Output: AttributeError
        get_value("foo.bar.baz2", obj, default=12)  # Output: 12

    """
    if not path:
        raise ValueError("Empty path")
    if not isinstance(path, str):
        raise TypeError("Path must be a string")

    value = obj
    current_path = []
    for part in path.split("."):
        current_path.append(part)
        curr_val = _get_attr(value, part)
        if curr_val is sentinel:
            curr_val = _get_item(value, part)
        if curr_val is sentinel:
            if default is sentinel:
                raise PathNotFoundError(".".join(current_path), obj)
            return default
        value = curr_val

    return value


def _get_attr(obj: Any, attr: str) -> Any:
    try:
        return getattr(obj, attr)
    except AttributeError:
        return sentinel


def _get_item(obj: Any, key: str) -> Any:
    try:
        return obj[key]
    except (KeyError, TypeError):
        return sentinel


T = TypeVar("T")
P = ParamSpec("P")


class _Lifespan:
    """
    Lifecycle manager for dependencies.

    Example
    -------
    .. code-block:: python

        from picodi.helpers import lifespan


        @lifespan
        def main(): ...


        @lifespan
        async def async_main(): ...


        @lifespan.sync()
        def main(): ...


        @lifespan.async_()
        async def async_main(): ...


        with lifespan.sync():
            ...

        async with lifespan.async_():
            ...
    """

    @overload
    def __call__(self, fn: Callable[P, T]) -> Callable[P, T]:
        """
        Decorator for functions

        :param fn: function to decorate.
        """

    @overload
    def __call__(
        self,
        fn: None = None,
        *,
        init_scope_class: LifespanScopeClass | None = SingletonScope,
        shutdown_scope_class: LifespanScopeClass | None = ManualScope,
    ) -> Callable[[Callable[P, T]], Callable[P, T]]:
        """Sync and Async context manager"""

    def __call__(
        self,
        fn: Callable[P, T] | None = None,
        *,
        init_scope_class: LifespanScopeClass | None = SingletonScope,
        shutdown_scope_class: LifespanScopeClass | None = ManualScope,
    ) -> Callable[P, T] | Callable[[Callable[P, T]], Callable[P, T]]:
        """
        Can be used as a decorator or a context manager.

        :param fn: function to decorate (if used as a decorator).
        :param init_scope_class: scope class for initialization
            (can be omitted by passing None).
        :param shutdown_scope_class: scope class for shutdown
            (can be omitted by passing None).
        :return: decorated function or decorator.
        """

        def decorator(fn: Callable[P, T]) -> Callable[P, T]:
            if asyncio.iscoroutinefunction(fn):
                return self.async_(  # type: ignore[return-value]
                    init_scope_class=init_scope_class,
                    shutdown_scope_class=shutdown_scope_class,
                )(fn)
            return self.sync(
                init_scope_class=init_scope_class,
                shutdown_scope_class=shutdown_scope_class,
            )(fn)

        return decorator if fn is None else decorator(fn)

    @contextlib.contextmanager
    def sync(
        self,
        *,
        init_scope_class: LifespanScopeClass | None = SingletonScope,
        shutdown_scope_class: LifespanScopeClass | None = ManualScope,
    ) -> Generator[None, None, None]:
        """
        :attr:`lifespan` can automatically detect if the decorated function
        is async or not. But if you want to force sync behavior, ``lifespan.sync``.

        :param init_scope_class: scope class for initialization
            (can be omitted by passing None).
        :param shutdown_scope_class: scope class for shutdown
            (can be omitted by passing None).
        """
        if init_scope_class is not None:
            picodi.init_dependencies(init_scope_class)
        try:
            yield
        finally:
            if shutdown_scope_class is not None:
                picodi.shutdown_dependencies(shutdown_scope_class)

    @contextlib.asynccontextmanager
    async def async_(
        self,
        *,
        init_scope_class: LifespanScopeClass | None = SingletonScope,
        shutdown_scope_class: LifespanScopeClass | None = ManualScope,
    ) -> AsyncGenerator[None, None]:
        """
        :attr:`lifespan` can automatically detect if the decorated function
        is async or not.
        But if you want to force async behavior, ``lifespan.async_``.

        :param init_scope_class: scope class for initialization
            (can be omitted by passing None).
        :param shutdown_scope_class: scope class for shutdown
            (can be omitted by passing None).
        """
        if init_scope_class is not None:
            await picodi.init_dependencies(init_scope_class)
        try:
            yield
        finally:
            if shutdown_scope_class is not None:
                await picodi.shutdown_dependencies(  # noqa: ASYNC102
                    shutdown_scope_class
                )


lifespan = _Lifespan()


@overload
def enter(dependency: Callable[[], Generator[T, None, None]]) -> ContextManager[T]: ...


@overload
def enter(  # type: ignore[overload-overlap]
    dependency: Callable[[], AsyncGenerator[T, None] | Coroutine[T, None, None]],
) -> AsyncContextManager[T]: ...


@overload
def enter(dependency: Callable[[], T]) -> ContextManager[T]: ...


def enter(
    dependency: Callable[
        [],
        Coroutine[T, None, None]
        | Generator[T, None, None]
        | AsyncGenerator[T, None]
        | T,
    ],
) -> AsyncContextManager[T] | ContextManager[T]:
    """
    Create a context manager from a dependency.

    Don't use (or use carefully) in production code. This function is mostly for
    cases when you can't use :func:`inject` decorator, for example in pytest fixtures.

    :param dependency: dependency to create a context manager from.
        Like with :func:`Provide` - don't call the dependency function here,
        just pass it.
    :return: sync or async context manager.

    Example
    -------

    .. code-block:: python

        from picodi.helpers import enter


        def get_42():
            yield 42


        with enter(get_42) as val:
            assert val == 42
    """
    dependency = _internal_registry.get_dep_or_override(dependency)
    result = dependency()

    if inspect.isasyncgen(result):

        @contextlib.asynccontextmanager
        @picodi.inject
        async def async_enter(
            dep: Any = picodi.Provide(dependency),
        ) -> AsyncGenerator[Any, None]:
            yield dep

        return async_enter()
    if inspect.isgenerator(result):

        @contextlib.contextmanager
        @picodi.inject
        def sync_enter(
            dep: Any = picodi.Provide(dependency),
        ) -> Generator[Any, None, None]:
            yield dep

        return sync_enter()

    return nullcontext(result)
