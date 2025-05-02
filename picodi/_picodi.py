from __future__ import annotations

import asyncio
import functools
import inspect
import logging
from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
from typing import Any, ParamSpec, TypeVar, cast

from picodi._internal import LazyResolver, _build_depend_tree, _wrapper_helper
from picodi._scopes import ManualScope, NullScope, ScopeType
from picodi._state import internal_registry, scopes
from picodi._types import (
    DependencyCallable,
    Depends,
    InitDependencies,
    LifespanScopeClass,
)
from picodi.support import NullAwaitable

logger = logging.getLogger("picodi")

T = TypeVar("T")
P = ParamSpec("P")
TC = TypeVar("TC", bound=Callable)


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


def inject(fn: Callable[P, T]) -> Callable[P, T]:
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
    signature = inspect.signature(fn)
    dependant = _build_depend_tree(Depends(fn))

    if inspect.iscoroutinefunction(fn) or inspect.isasyncgenfunction(fn):

        @functools.wraps(fn)
        async def fun_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            gen = _wrapper_helper(
                dependant,
                signature,
                is_async=True,
                args=args,
                kwargs=kwargs,
            )
            value, action = next(gen)
            result = None
            exceptions = []
            while True:
                if inspect.iscoroutine(value):
                    try:
                        value = await value
                    except Exception as e:  # noqa: PIE786
                        exceptions.append(e)

                if action == "result":
                    result = value
                try:
                    value, action = gen.send(value)
                except StopIteration:
                    break
            if exceptions:
                # TODO use `ExceptionGroup` after dropping 3.10 support
                raise exceptions[0]
            return cast("T", result)

        wrapper = fun_wrapper

        if inspect.isasyncgenfunction(fn):

            @functools.wraps(fn)
            async def gen_wrapper(
                *args: P.args, **kwargs: P.kwargs
            ) -> AsyncGenerator[T, None]:
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
            gen = _wrapper_helper(
                dependant,
                signature,
                is_async=False,
                args=args,
                kwargs=kwargs,
            )
            value, action = next(gen)
            result = None
            while True:
                if action == "result":
                    result = value
                try:
                    value, action = gen.send(value)
                except StopIteration:
                    break
            return cast("T", result)

        wrapper = fun_wrapper

        if inspect.isgeneratorfunction(fn):

            @functools.wraps(fn)
            def gen_wrapper(
                *args: P.args, **kwargs: P.kwargs
            ) -> Generator[T, None, None]:
                yield from fun_wrapper(*args, **kwargs)  # type: ignore[misc]

            wrapper = gen_wrapper  # type: ignore[assignment]

    return wrapper  # type: ignore[return-value]


def dependency(*, scope_class: type[ScopeType] = NullScope) -> Callable[[TC], TC]:
    """
    Decorator to declare a dependency. You don't need to use it with default arguments,
    use it only if you want to change the scope of the dependency.
    Should be placed last in the decorator chain (on top).

    :param scope_class: specify the scope class to use for the dependency. Default is
        :class:`NullScope`.
        Picodi additionally provides a few built-in scopes:
        :class:`SingletonScope`, :class:`ContextVarScope`.
    """

    if scope_class not in scopes:
        scopes[scope_class] = scope_class()

    def decorator(fn: TC) -> TC:
        internal_registry.add(
            fn,
            scope_class=scope_class,
        )
        return fn

    return decorator


def init_dependencies(dependencies: InitDependencies) -> Awaitable:
    """
    Call this function to init dependencies. Usually, it should be called
    when your application is starting up.

    This function works both for synchronous and asynchronous dependencies.
    If you call it without ``await``, it will initialize only sync dependencies.
    If you call it ``await init_dependencies(...)``, it will initialize both sync and
    async dependencies.

    :param dependencies: iterable of dependencies to initialize.
    """
    if callable(dependencies):
        dependencies = dependencies()

    async_deps: list[Awaitable] = []
    for dep in dependencies:
        provider = internal_registry.get(dep)
        resolver = LazyResolver(provider)
        value = resolver(provider.is_async)
        if provider.is_async:
            async_deps.append(value)

    if async_deps:
        # asyncio.gather runs coros in different tasks with different context
        #   we can run them in current context with contextvars.copy_context()
        #   but in this case `ContextVarScope` will save values in the wrong context.
        #   So we fix it in dirty way by running all coros one by one until
        #   come up with better solution.
        async def init_all() -> None:
            for dep in async_deps:
                await dep

        return init_all()
    return NullAwaitable()


def shutdown_dependencies(scope_class: LifespanScopeClass = ManualScope) -> Awaitable:
    """
    Call this function to close dependencies. Usually, it should be called
    when your application is shut down.

    This function works both for synchronous and asynchronous dependencies.
    If you call it without ``await``, it will shutdown only sync dependencies.
    If you call it ``await shutdown_dependencies()``, it will shutdown both
    sync and async dependencies.

    If you not pass any arguments, it will shutdown subclasses of :class:`ManualScope`.

    :param scope_class: you can specify the scope class to shutdown. If passed -
        only dependencies of this scope class and its subclasses will be shutdown.
    """
    tasks = [
        instance.shutdown()  # type: ignore[call-arg]
        for klass, instance in scopes.items()
        if issubclass(klass, scope_class)
    ]
    if all(isinstance(task, NullAwaitable) for task in tasks):
        return NullAwaitable()
    return asyncio.gather(*tasks)
