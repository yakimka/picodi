from __future__ import annotations

import asyncio
import functools
import inspect
from collections.abc import Awaitable, Callable, Coroutine, Generator
from contextlib import (
    AsyncExitStack,
    ExitStack,
    asynccontextmanager,
    contextmanager,
    nullcontext,
)
from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncContextManager,
    ContextManager,
    ParamSpec,
    TypeVar,
)

from nanodi.scopes import NullScope, Scope, SingletonScope

if TYPE_CHECKING:
    from inspect import BoundArguments

Dependency = Callable[..., Any]
T = TypeVar("T")
P = ParamSpec("P")
TC = TypeVar("TC", bound=Callable)

_unset = object()
_exit_stack = ExitStack()
_async_exit_stack = AsyncExitStack()
_resources: list[Depends] = []
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
    if inspect.iscoroutinefunction(fn):

        @functools.wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            bound = signature.bind(*args, **kwargs)
            bound.apply_defaults()
            exit_stack = AsyncExitStack()
            for depends, names, get_value in _resolve_depends(
                bound, exit_stack, is_async=True
            ):
                if depends.use_cache:
                    value = await get_value()
                    bound.arguments.update({name: value for name in names})
                else:
                    bound.arguments.update({name: await get_value() for name in names})

            async with exit_stack:
                result = await fn(*bound.args, **bound.kwargs)
            return result

    else:

        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            bound = signature.bind(*args, **kwargs)
            bound.apply_defaults()
            exit_stack = ExitStack()
            for depends, names, get_value in _resolve_depends(
                bound, exit_stack, is_async=False
            ):
                if depends.use_cache:
                    value = get_value()
                    bound.arguments.update({name: value for name in names})
                else:
                    bound.arguments.update({name: get_value() for name in names})

            with exit_stack:
                result = fn(*bound.args, **bound.kwargs)
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
    if not inspect.isgeneratorfunction(fn) and not inspect.isasyncgenfunction(fn):
        raise TypeError("Resource should be a generator function")
    fn._scope_ = "singleton"  # type: ignore[attr-defined] # noqa: SF01
    _resources.append(Depends.from_dependency(fn, use_cache=True))
    return fn


def init_resources() -> Awaitable:
    """
    Call this function to close all resources. Usually, it should be called
    when your application is shutting down.
    """
    async_resources = []
    for depends in _resources:
        if depends.is_async:
            async_resources.append(
                _get_value_from_depends_async(depends, _async_exit_stack)
            )
        else:
            _get_value_from_depends(depends, _exit_stack)

    return asyncio.gather(*async_resources)


def shutdown_resources() -> Awaitable:
    """
    Call this function to close all resources. Usually, it should be called
    when your application is shutting down.
    """
    _exit_stack.close()
    return _async_exit_stack.aclose()


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

        return cls(dependency, use_cache, context_manager, is_async)


def _resolve_depends(
    bound: BoundArguments, exit_stack: AsyncExitStack | ExitStack, is_async: bool
) -> Generator[tuple[Depends, list[str], Callable[[], Any]], None, None]:
    dependencies: dict[Depends, list[str]] = {}
    for name, value in bound.arguments.items():
        if isinstance(value, Depends):
            dependencies.setdefault(value, []).append(name)

    get_val = _get_value_from_depends_async if is_async else _get_value_from_depends

    for depends, names in dependencies.items():
        get_value = functools.partial(get_val, depends, exit_stack)  # type: ignore
        yield depends, names, get_value


def _get_value_from_depends(
    depends: Depends,
    local_exit_stack: ExitStack,
) -> Any:
    scope_name = depends.get_scope_name()
    scope = _scopes[scope_name]
    try:
        value = scope.get(depends.dependency)
    except KeyError:
        context_manager = depends.value_as_context_manager()
        exit_stack = local_exit_stack
        if scope_name == "singleton":
            exit_stack = _exit_stack
        if depends.is_async:
            value = depends.dependency
        else:
            value = exit_stack.enter_context(context_manager)
            scope.set(depends.dependency, value)
    return value


async def _get_value_from_depends_async(
    depends: Depends,
    local_exit_stack: AsyncExitStack,
) -> Any:
    scope_name = depends.get_scope_name()
    scope = _scopes[scope_name]
    try:
        value = scope.get(depends.dependency)
    except KeyError:
        context_manager = depends.value_as_context_manager()
        exit_stack = local_exit_stack
        if scope_name == "singleton":
            exit_stack = _async_exit_stack
        if depends.is_async:
            value = await exit_stack.enter_async_context(context_manager)
        else:
            value = exit_stack.enter_context(context_manager)
        scope.set(depends.dependency, value)
    return value
