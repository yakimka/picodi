from __future__ import annotations

import functools
import inspect
from collections.abc import Callable, Coroutine, Generator
from contextlib import (
    AsyncExitStack,
    ExitStack,
    asynccontextmanager,
    contextmanager,
    nullcontext,
)
from dataclasses import dataclass, field
from typing import Any, AsyncContextManager, ContextManager, ParamSpec, TypeVar

from nanodi.scopes import NullScope, Scope, SingletonScope

Dependency = Callable[..., Any]
T = TypeVar("T")
P = ParamSpec("P")
TC = TypeVar("TC", bound=Callable)

_unset = object()
_exit_stack = ExitStack()
_async_exit_stack = AsyncExitStack()
_resources_result_cache: dict[Dependency, Any] = {}
_scopes: dict[str, Scope] = {
    "null": NullScope(),
    "singleton": SingletonScope(),
}


def Provide(dependency: Dependency, /, use_cache: bool = True) -> Any:  # noqa: N802
    """
    Declare a provider.
    It takes a single "dependency" callable (like a function).
    Don't call it directly, nanodi will call it for you.
    Dependency can be a regular function or a generator with one yield.
    If the dependency is a generator, it will be used as a context manager.
    Any generator that is valid for `contextlib.contextmanager`
    can be used as a dependency.

    Example:
    ```
    from functools import lru_cache
    from nanodi import Provide, inject
    from my_conf import Settings

    def get_db():
        yield "db connection"
        print("closing db connection")

    @lru_cache # for calling the dependency only once
    def get_settings():
        return Settings()

    @inject
    def my_service(db=Provide(get_db), settings=Provide(get_settings)):
        assert db == "db connection"
        assert isinstance(settings, Settings)
    ```
    """
    if not getattr(dependency, "_scope_", None):
        dependency._scope_ = "null"  # type: ignore[attr-defined] # noqa: SF01
    return Depends.from_dependency(dependency, use_cache)


def inject(fn: Callable[P, T]) -> Callable[P, T | Coroutine[Any, Any, T]]:
    """
    Decorator to inject dependencies into a function.
    Use it in combination with `Provide` to declare dependencies.

    Example:
    ```
    from nanodi import inject, Provide

    @inject
    def my_service(db=Provide(some_dependency_func)):
        ...
    ```
    """
    signature = inspect.signature(fn)
    is_async_function = inspect.iscoroutinefunction(fn)

    def func_wrapper_with_exit_stack(*args: P.args, **kwargs: P.kwargs) -> T:
        bound = signature.bind(*args, **kwargs)
        bound.apply_defaults()

        dependencies: dict[Depends, list[str]] = {}
        for name, value in bound.arguments.items():
            if isinstance(value, Depends):
                dependencies.setdefault(value, []).append(name)

        if is_async_function:
            exit_stack = AsyncExitStack()
        else:
            exit_stack = ExitStack()
        for depends, names in dependencies.items():
            get_value = functools.partial(_get_value_from_depends, depends, exit_stack)
            if depends.use_cache:
                value = get_value()
                get_value = functools.partial(lambda v: v, value)
            bound.arguments.update({name: get_value() for name in names})

        return fn(*bound.args, **bound.kwargs), exit_stack

    if is_async_function:

        @functools.wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            result, exit_stack = func_wrapper_with_exit_stack(*args, **kwargs)
            async with exit_stack:
                return await result

    else:

        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            result, exit_stack = func_wrapper_with_exit_stack(*args, **kwargs)
            with exit_stack:
                return result

    return wrapper


def resource(fn: TC) -> TC:
    """
    Decorator to declare a resource. Resource is a dependency that should be
    called only once, cached and shared across the application.
    On shutdown, all resources will be closed
    (you need to call `shutdown_resources` manually).
    Use it with a dependency generator function to declare a resource.

    Example:
    ```
    from nanodi import resource

    # will be called only once
    @resource
    def get_db():
        yield "db connection"
        print("closing db connection")
    ```
    """
    fn._scope_ = "singleton"  # type: ignore[attr-defined] # noqa: SF01
    return fn


def shutdown_resources() -> None:
    """
    Call this function to close all resources. Usually, it should be called
    when your application is shutting down.
    """
    _exit_stack.close()


@dataclass(frozen=True)
class Depends:
    dependency: Dependency
    use_cache: bool
    context_manager: ContextManager | AsyncContextManager | None = field(compare=False)
    is_async: bool = field(compare=False)

    def get_scope_name(self) -> str:
        return self.dependency._scope_  # type: ignore[attr-defined] # noqa: SF01

    def value_as_context_manager(self) -> Any:
        if self.context_manager:
            return self.context_manager
        return nullcontext(self.dependency())

    @classmethod
    def from_dependency(cls, dependency: Dependency, use_cache: bool) -> Depends:
        context_manager: ContextManager | AsyncContextManager | None = None
        is_async = False
        if inspect.isasyncgenfunction(dependency):
            context_manager = asynccontextmanager(dependency)()
            is_async = True
        elif inspect.isgeneratorfunction(dependency):
            context_manager = contextmanager(dependency)()

        if getattr(dependency, "_scope_", None) == "singleton":
            _resources_result_cache[dependency] = _unset
        return cls(dependency, use_cache, context_manager, is_async)


def _get_value_from_depends(
    depends: Depends,
    local_exit_stack: ExitStack | AsyncExitStack,
) -> Any:
    scope_name = depends.get_scope_name()
    scope = _scopes[scope_name]
    try:
        value = scope.get(depends.dependency)
    except KeyError:
        context_manager = depends.value_as_context_manager()
        exit_stack = local_exit_stack
        if scope_name == "singleton":
            if isinstance(exit_stack, AsyncExitStack):
                exit_stack = _async_exit_stack
            else:
                exit_stack = _exit_stack
        if depends.is_async:
            value = exit_stack.enter_async_context(context_manager)
        else:
            value = exit_stack.enter_context(context_manager)
        scope.set(depends.dependency, value)
    return value
