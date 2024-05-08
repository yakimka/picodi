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
    cast,
)

from picodi.scopes import ExitStack, NullScope, Scope, SingletonScope

if TYPE_CHECKING:
    from inspect import BoundArguments, Signature

try:
    import fastapi.params
except ImportError:
    fastapi = None  # type: ignore[assignment]


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
    return Depends.from_dependency(dependency)


def inject(fn: Callable[P, T]) -> Callable[P, T]:
    """
    Decorator to inject dependencies into a function.
    Use it in combination with `Provide` to declare dependencies.
    Should be placed first in the decorator chain (on bottom).

    Example:
    ```
    from picodi import inject, Provide

    @inject
    def my_service(db=Provide(some_dependency_func)):
        ...
    ```
    """
    signature = inspect.signature(fn)
    if inspect.iscoroutinefunction(fn) or inspect.isasyncgenfunction(fn):

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
                result_or_gen = fn(*bound.args, **bound.kwargs)
                if inspect.isasyncgen(result_or_gen):
                    result = result_or_gen
                else:
                    result = await result_or_gen  # type: ignore[misc]
            return cast("T", result)

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
    Should be placed last in the decorator chain (on top).
    """
    fn._picodi_scope_ = "singleton"  # type: ignore[attr-defined] # noqa: SF01
    with _lock:
        _resources.append(Depends.from_dependency(fn))
    return fn


def init_resources() -> Awaitable:
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

    return asyncio.gather(*async_resources)


def shutdown_resources() -> Awaitable:
    """
    Call this function to close all resources. Usually, it should be called
    when your application is shut down.
    """
    if _is_async_environment():
        tasks = [scope.exit_stack.close() for scope in _scopes.values()]
        return asyncio.gather(*tasks)  # type: ignore[arg-type]

    for scope in _scopes.values():
        scope.exit_stack.close(only_sync=True)
    return asyncio.gather(*[])


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
    is_async: bool = field(compare=False)

    @classmethod
    def from_dependency(cls, dependency: Dependency) -> Depends:
        return cls(
            dependency,
            inspect.iscoroutinefunction(dependency)
            or inspect.isasyncgenfunction(dependency),
        )

    def get_scope(self) -> Scope:
        scope_name = getattr(self.dependency, "_picodi_scope_", "null")
        return _scopes[scope_name]

    def resolve_value(self) -> Any:
        scope = self.get_scope()
        value_or_gen = self.dependency()
        if self.is_async:

            async def resolve_value_inner() -> Any:
                value_or_gen_ = value_or_gen
                if inspect.iscoroutine(value_or_gen):
                    value_or_gen_ = await value_or_gen_
                if inspect.isasyncgen(value_or_gen_):
                    context_manager = asynccontextmanager(
                        lambda *args, **kwargs: value_or_gen_
                    )
                    return await scope.exit_stack.enter_context(context_manager())
                return value_or_gen_

            return resolve_value_inner()

        if inspect.isgenerator(value_or_gen):
            context_manager = contextmanager(lambda *args, **kwargs: value_or_gen)
            return scope.exit_stack.enter_context(context_manager())
        return value_or_gen

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
