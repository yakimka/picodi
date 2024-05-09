from __future__ import annotations

import asyncio
import functools
import inspect
import threading
from collections.abc import Awaitable, Callable
from contextlib import asynccontextmanager, contextmanager
from dataclasses import asdict, dataclass, field
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

from picodi.scopes import GlobalScope, NullScope, Scope, SingletonScope

if TYPE_CHECKING:
    from inspect import BoundArguments, Signature

DependencyCallable = Callable[..., Any]
T = TypeVar("T")
P = ParamSpec("P")
TC = TypeVar("TC", bound=Callable)


_unset = object()
_lock = threading.RLock()
_registry: dict[DependencyCallable, Provider] = {}
_scopes: dict[type[Scope], Scope] = {
    NullScope: NullScope(),
    SingletonScope: SingletonScope(),
}


def Provide(dependency: DependencyCallable, /) -> Any:  # noqa: N802
    """
    Declare a provider.
    It takes a single "dependency" callable (like a function).
    Don't call it directly, picodi will call it for you.
    DependencyCallable can be a regular function or a generator with one yield.
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
    with _lock:
        if dependency not in _registry:
            _registry[dependency] = Provider.from_dependency(dependency, in_use=True)
        elif not _registry[dependency].in_use:
            _registry[dependency] = _registry[dependency].replace(in_use=True)

    return Dependency(dependency)


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

            result_or_gen = fn(*bound.args, **bound.kwargs)
            if inspect.isasyncgen(result_or_gen):
                result = result_or_gen
            else:
                result = await result_or_gen  # type: ignore[misc]

            for scope in _scopes.values():
                await scope.close_local()
            return cast("T", result)

    else:

        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            bound, dep_arguments = _arguments_to_getters(
                args, kwargs, signature, is_async=False
            )
            for name, get_value in dep_arguments.items():
                bound.arguments[name] = get_value()

            result = fn(*bound.args, **bound.kwargs)
            for scope in _scopes.values():
                scope.close_local()
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
    with _lock:
        if fn in _registry:
            provider = _registry[fn].replace(scope_class=SingletonScope)
        else:
            provider = Provider.from_dependency(
                fn, scope_class=SingletonScope, in_use=False
            )
        _registry[fn] = provider
    return fn


def init_resources() -> Awaitable:
    """
    Call this function to close all resources. Usually, it should be called
    when your application is shutting down.
    """
    async_resources = []
    for provider in _registry.values():
        if provider.in_use and issubclass(provider.scope_class, GlobalScope):
            if provider.is_async:
                async_resources.append(_resolve_value_async(provider))
            else:
                _resolve_value(provider)

    return asyncio.gather(*async_resources)


def shutdown_resources() -> Awaitable:
    """
    Call this function to close all resources. Usually, it should be called
    when your application is shut down.
    """
    tasks = [scope.close_global() for scope in _scopes.values()]
    return asyncio.gather(*tasks)


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
class Dependency:
    original: DependencyCallable

    def __call__(self) -> Dependency:
        return self

    def get_provider(self) -> Provider:
        return _registry[self.original]


@dataclass(frozen=True)
class Provider:
    dependency: DependencyCallable
    is_async: bool = field(compare=False)
    scope_class: type[Scope] = field(compare=False)
    in_use: bool = field(compare=False)

    @classmethod
    def from_dependency(
        cls,
        dependency: DependencyCallable,
        scope_class: type[Scope] = NullScope,
        in_use: bool = False,
    ) -> Provider:
        is_async = inspect.iscoroutinefunction(
            dependency
        ) or inspect.isasyncgenfunction(dependency)
        return cls(
            dependency=dependency,
            is_async=is_async,
            scope_class=scope_class,
            in_use=in_use,
        )

    def replace(
        self, scope_class: type[Scope] | None = None, in_use: bool | None = None
    ) -> Provider:
        kwargs = asdict(self)
        if scope_class is not None:
            kwargs["scope_class"] = scope_class
        if in_use is not None:
            kwargs["in_use"] = in_use
        return Provider(**kwargs)

    def get_scope(self) -> Scope:
        return _scopes[self.scope_class]

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


def _arguments_to_getters(
    args: P.args, kwargs: P.kwargs, signature: Signature, is_async: bool
) -> tuple[BoundArguments, dict[str, Callable[[], Any]]]:
    bound = signature.bind(*args, **kwargs)
    bound.apply_defaults()
    dependencies: dict[Provider, list[str]] = {}
    for name, value in bound.arguments.items():
        if isinstance(value, Dependency):
            dependencies.setdefault(value.get_provider(), []).append(name)

    get_val = _resolve_value_async if is_async else _resolve_value

    dep_arguments = {}
    for provider, names in dependencies.items():
        get_value: Callable = functools.partial(get_val, provider)
        for name in names:
            dep_arguments[name] = get_value

    return bound, dep_arguments


def _resolve_value(provider: Provider) -> Any:
    scope = provider.get_scope()
    try:
        value = scope.get(provider.dependency)
    except KeyError:
        if provider.is_async:
            value = provider.dependency()
        else:
            with _lock:
                try:
                    value = scope.get(provider.dependency)
                except KeyError:
                    value = provider.resolve_value()
                    scope.set(provider.dependency, value)
    return value


async def _resolve_value_async(provider: Provider) -> Any:
    scope = provider.get_scope()
    try:
        value = scope.get(provider.dependency)
    except KeyError:
        with _lock:
            try:
                value = scope.get(provider.dependency)
            except KeyError:
                value = provider.resolve_value()
                if provider.is_async:
                    value = await value
                scope.set(provider.dependency, value)
    return value
