from __future__ import annotations

import asyncio
import functools
import inspect
import threading
from collections.abc import Awaitable, Callable, Coroutine, Generator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Any,
    AsyncContextManager,
    ContextManager,
    ParamSpec,
    TypeVar,
)

from picodi.scopes import ExitStack, NullScope, Scope, SingletonScope

if TYPE_CHECKING:
    from inspect import BoundArguments

Dependency = Callable[..., Any]
T = TypeVar("T")
P = ParamSpec("P")
TC = TypeVar("TC", bound=Callable)


_unset = object()
_resources: list[Depends] = []
_lock = threading.RLock()
_scopes: dict[str, Scope] = {
    "null": NullScope(),
    "singleton": SingletonScope(),
}


def Provide(dependency: Dependency, /) -> Any:  # noqa: N802
    """
    Declare a provider.
    It takes a single "dependency" callable (like a function).
    Don't call it directly, picodi will call it for you.
    Dependency can be a regular function or a generator with one yield.
    If the dependency is a generator, it will be used as a context manager.
    Any generator that is valid for `contextlib.contextmanager`
    can be used as a dependency.

    Example:
    ```
    from picodi import Provide, inject

    def get_db():
        yield "db connection"
        print("closing db connection")

    @inject
    def my_service(db: str = Provide(get_db)):
        assert db == "db connection"
    ```
    """
    if not getattr(dependency, "_scope_", None):
        dependency._scope_ = "null"  # type: ignore[attr-defined] # noqa: SF01
    return Depends.from_dependency(dependency)


def inject(fn: Callable[P, T]) -> Callable[P, T | Coroutine[Any, Any, T]]:
    """
    Decorator to inject dependencies into a function.
    Use it in combination with `Provide` to declare dependencies.

    Example:
    ```
    from picodi import inject, Provide

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
            for names, get_value in _arguments_to_getter(bound, is_async=True):
                bound.arguments.update({name: await get_value() for name in names})

            async with ExitStack() as stack:
                for scope in _scopes.values():
                    await stack.enter_context(scope)
                result = await fn(*bound.args, **bound.kwargs)
            return result

    else:

        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            bound = signature.bind(*args, **kwargs)
            bound.apply_defaults()
            for names, get_value in _arguments_to_getter(bound, is_async=False):
                bound.arguments.update({name: get_value() for name in names})

            with ExitStack() as stack:
                for scope in _scopes.values():
                    stack.enter_context(scope, only_sync=True)
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
    """
    if not inspect.isgeneratorfunction(fn) and not inspect.isasyncgenfunction(fn):
        raise TypeError("Resource should be a generator function")
    fn._scope_ = "singleton"  # type: ignore[attr-defined] # noqa: SF01
    with _lock:
        _resources.append(Depends.from_dependency(fn))
    return fn


def init_resources() -> Awaitable | None:
    """
    Call this function to close all resources. Usually, it should be called
    when your application is shutting down.
    """
    async_resources = []
    for depends in _resources:
        if depends.is_async:
            async_resources.append(_resolve_value_async(depends))
        else:
            _resolve_value(depends)

    if _is_async_environment():
        return asyncio.gather(*async_resources)
    return None


def shutdown_resources() -> Awaitable | None:
    """
    Call this function to close all resources. Usually, it should be called
    when your application is shutting down.
    """
    if _is_async_environment():
        return asyncio.gather(*[scope.exit_stack.close() for scope in _scopes.values()])

    for scope in _scopes.values():
        scope.exit_stack.close(only_sync=True)
    return None


CallableManager = Callable[..., AsyncContextManager | ContextManager]


@dataclass(frozen=True)
class Depends:
    dependency: Dependency
    context_manager: CallableManager | None = field(compare=False)
    is_async: bool = field(compare=False)

    @classmethod
    def from_dependency(cls, dependency: Dependency) -> Depends:
        context_manager: Callable | None = None
        is_async = inspect.iscoroutinefunction(dependency)
        if inspect.isasyncgenfunction(dependency):
            context_manager = asynccontextmanager(dependency)
            is_async = True
        elif inspect.isgeneratorfunction(dependency):
            context_manager = contextmanager(dependency)

        return cls(dependency, context_manager, is_async)

    def get_scope(self) -> Scope:
        scope_name = self.dependency._scope_  # type: ignore[attr-defined] # noqa: SF01
        return _scopes[scope_name]

    def resolve_value(self) -> Any:
        scope = self.get_scope()
        if self.context_manager:
            return scope.exit_stack.enter_context(self.context_manager())
        return self.dependency()


def _arguments_to_getter(
    bound: BoundArguments, is_async: bool
) -> Generator[tuple[list[str], Callable[[], Any]], None, None]:
    dependencies: dict[Depends, list[str]] = {}
    for name, value in bound.arguments.items():
        if isinstance(value, Depends):
            dependencies.setdefault(value, []).append(name)

    get_val = _resolve_value_async if is_async else _resolve_value

    for depends, names in dependencies.items():
        get_value = functools.partial(get_val, depends)  # type: ignore
        yield names, get_value


def _resolve_value(depends: Depends) -> Any:
    scope = depends.get_scope()
    try:
        value = scope.get(depends.dependency)
    except KeyError:
        if depends.is_async:
            value = depends.dependency()
        else:
            with _lock:
                try:
                    value = scope.get(depends.dependency)
                except KeyError:
                    value = depends.resolve_value()
                    scope.set(depends.dependency, value)
    return value


async def _resolve_value_async(depends: Depends) -> Any:
    scope = depends.get_scope()
    try:
        value = scope.get(depends.dependency)
    except KeyError:
        with _lock:
            try:
                value = scope.get(depends.dependency)
            except KeyError:
                value = depends.resolve_value()
                if depends.is_async:
                    value = await value
                scope.set(depends.dependency, value)
    return value


def _is_async_environment() -> bool:
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return False
    return True
