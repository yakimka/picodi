from __future__ import annotations

import functools
import inspect
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar, cast, overload

from picodi._internal import (
    async_injection_context,
    build_depend_tree,
    get_storage_from_registry,
    sync_injection_context,
)
from picodi._registry import Registry
from picodi._registry import registry as default_registry
from picodi._types import DependencyCallable, Depends

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable, Generator

T = TypeVar("T")
P = ParamSpec("P")


def Provide(dependency: DependencyCallable, /) -> Any:  # noqa: N802
    """
    Declare a provider.
    It takes a single "dependency" callable (like a function).
    Don't call it directly, picodi will call it for you.

    :param dependency: can be a regular function or a generator with one yield.
        If the dependency is a generator, it will be used as a context manager.
        Any generator that is valid for :func:`python:contextlib.contextmanager`
        can be used as a dependency.

    Example
    -------
    .. code-block:: python

        from picodi import Provide, inject


        def get_db():
            yield "db connection"
            print("closing db connection")


        @inject
        def my_service(db: str = Provide(get_db)):
            assert db == "db connection"
    """
    return Depends(dependency)


@overload
def inject(fn: Callable[P, T]) -> Callable[P, T]:
    """Decorator to inject dependencies into a function."""


@overload
def inject(
    fn: None = None,
    *,
    registry: Registry | None = None,
) -> Callable[[Callable[P, T]], Callable[P, T]]:
    """Decorator fabric to inject dependencies into a function."""


def inject(
    fn: Callable[P, T] | None = None, *, registry: Registry | None = None
) -> Callable[P, T] | Callable[[Callable[P, T]], Callable[P, T]]:
    """
    Decorator to inject dependencies into a function.
    Use it in combination with :func:`Provide` to declare dependencies.
    Should be placed first in the decorator chain (on bottom).

    :param fn: function to decorate.

    Example
    -------
    .. code-block:: python

        from picodi import inject, Provide


        @inject
        def my_service(db=Provide(some_dependency_func)):
            pass
    """
    if registry is None:
        registry = default_registry

    def inject_decorator(fn: Callable[P, T]) -> Callable[P, T]:
        signature = inspect.signature(fn)
        storage = get_storage_from_registry(registry)
        dependant = build_depend_tree(fn, storage=storage)

        if inspect.iscoroutinefunction(fn) or inspect.isasyncgenfunction(fn):

            @functools.wraps(fn)
            async def fun_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                async with async_injection_context(
                    dependant,
                    signature,
                    registry,
                    args=args,
                    kwargs=kwargs,
                ) as result:
                    return cast("T", result)

            wrapper = fun_wrapper

            if inspect.isasyncgenfunction(fn):

                @functools.wraps(fn)
                async def gen_wrapper(
                    *args: P.args, **kwargs: P.kwargs
                ) -> AsyncGenerator[T]:
                    result = await fun_wrapper(*args, **kwargs)
                    async for value in result:  # type: ignore[attr-defined]
                        try:
                            yield value
                        except Exception as e:  # noqa: PIE786
                            try:
                                await result.athrow(e)  # type: ignore[attr-defined]
                            except StopAsyncIteration:
                                break

                wrapper = gen_wrapper  # type: ignore[assignment]

        else:

            @functools.wraps(fn)
            def fun_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
                with sync_injection_context(
                    dependant,
                    signature,
                    registry,
                    args=args,
                    kwargs=kwargs,
                ) as result:
                    return cast("T", result)

            wrapper = fun_wrapper

            if inspect.isgeneratorfunction(fn):

                @functools.wraps(fn)
                def gen_wrapper(*args: P.args, **kwargs: P.kwargs) -> Generator[T]:
                    yield from fun_wrapper(*args, **kwargs)  # type: ignore[misc]

                wrapper = gen_wrapper  # type: ignore[assignment]

        return wrapper  # type: ignore[return-value]

    return inject_decorator if fn is None else inject_decorator(fn)
