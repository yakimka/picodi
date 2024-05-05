from __future__ import annotations

import asyncio
import functools
import inspect
import threading
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass, field
from functools import wraps
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
    from inspect import BoundArguments, Signature
    from types import ModuleType

fastapi: ModuleType | None = None

try:
    import fastapi.params
except ImportError:
    fastapi = None


try:
    import fastapi.params
except ImportError:
    fastapi = None


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


def _is_fastapi_dependency(value: Any) -> bool:
    return bool(fastapi and isinstance(value, fastapi.params.Depends))


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
    if not getattr(dependency, "_picodi_scope_", None):
        dependency._picodi_scope_ = "null"  # type: ignore[attr-defined] # noqa: SF01
    return Depends.from_dependency(dependency)


def inject(fn: Callable[P, T]) -> Callable[P, T]:
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
            bound, dep_arguments = _arguments_to_getters(
                args, kwargs, signature, is_async=True
            )
            for name, get_value in dep_arguments.items():
                bound.arguments[name] = await get_value()

            async with ExitStack() as stack:
                for scope in _scopes.values():
                    await stack.enter_context(scope)
                result = await fn(*bound.args, **bound.kwargs)
            return result

    else:

        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            bound, dep_arguments = _arguments_to_getters(
                args, kwargs, signature, is_async=False
            )
            for name, get_value in dep_arguments.items():
                bound.arguments[name] = get_value()

            with ExitStack() as stack:
                for scope in _scopes.values():
                    stack.enter_context(scope, sync_first=True)
                result = fn(*bound.args, **bound.kwargs)
            return result

    wrapper._picodi_inject_ = True  # type: ignore[attr-defined] # noqa: SF01
    return wrapper  # type: ignore[return-value]


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
    fn._picodi_scope_ = "singleton"  # type: ignore[attr-defined] # noqa: SF01
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
    when your application is shut down.
    """
    if _is_async_environment():
        tasks = [scope.exit_stack.close() for scope in _scopes.values()]
        return asyncio.gather(*tasks)  # type: ignore[arg-type]

    for scope in _scopes.values():
        scope.exit_stack.close(only_sync=True)
    return None


def make_dependency(fn: Callable[P, T], *args: Any, **kwargs: Any) -> Callable[..., T]:
    signature = inspect.signature(fn)
    bound = signature.bind(*args, **kwargs)
    bound.apply_defaults()

    if not getattr(fn, "_picodi_inject_", None):
        fn = inject(fn)

    @wraps(fn)
    def wrapper(*args_in: P.args, **kwargs_in: P.kwargs) -> T:
        bound_inner = signature.bind_partial(*args_in, **kwargs_in)
        bound.arguments.update(bound_inner.arguments)
        return fn(*bound.args, **bound.kwargs)

    return wrapper


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
        scope_name = (
            self.dependency._picodi_scope_  # type: ignore[attr-defined] # noqa: SF01
        )
        return _scopes[scope_name]

    def resolve_value(self) -> Any:
        scope = self.get_scope()
        if self.context_manager:
            return scope.exit_stack.enter_context(self.context_manager())
        return self.dependency()

    def __call__(self) -> Depends:
        return self


def _arguments_to_getters(
    args: P.args, kwargs: P.kwargs, signature: Signature, is_async: bool
) -> tuple[BoundArguments, dict[str, Callable[[], Any]]]:
    bound = signature.bind(*args, **kwargs)
    bound.apply_defaults()
    dependencies: dict[Depends, list[str]] = {}
    for name, value in bound.arguments.items():
        if _is_fastapi_dependency(value):
            value = value.dependency
        if isinstance(value, Depends):
            dependencies.setdefault(value, []).append(name)

    get_val = _resolve_value_async if is_async else _resolve_value

    dep_arguments = {}
    for depends, names in dependencies.items():
        get_value: Callable = functools.partial(get_val, depends)
        for name in names:
            dep_arguments[name] = get_value

    return bound, dep_arguments


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
