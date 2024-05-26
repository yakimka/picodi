from __future__ import annotations

import asyncio
import functools
import inspect
import threading
from collections.abc import Awaitable, Callable, Generator, Iterable, Iterator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import asdict, dataclass
from typing import TYPE_CHECKING, Any, NamedTuple, ParamSpec, TypeVar, cast

from picodi._internal import DummyAwaitable
from picodi._scopes import (
    GlobalScope,
    NullScope,
    ParentCallScope,
    Scope,
    SingletonScope,
)

if TYPE_CHECKING:
    from inspect import BoundArguments, Signature

DependencyCallable = Callable[..., Any]
T = TypeVar("T")
P = ParamSpec("P")
TC = TypeVar("TC", bound=Callable)

unset = object()


class RegistryStorage:
    def __init__(self) -> None:
        self.deps: dict[DependencyCallable, Provider] = {}
        self.overrides: dict[DependencyCallable, DependencyCallable] = {}
        self.lock = threading.RLock()

    def __iter__(self) -> Iterator[Provider]:
        return iter(self.deps.values())


class InternalRegistry:
    def __init__(self, storage: RegistryStorage) -> None:
        self._storage = storage

    def add(
        self,
        dependency: DependencyCallable,
        scope_class: type[Scope] = NullScope,
        in_use: bool = True,
        override_scope: bool = False,
    ) -> None:
        """
        Add a dependency to the registry. If the dependency is already in the registry,
        it `in_use` flag can be updated, but the scope class cannot be changed.
        If the dependency is not in the registry, it will be added with the provided
        scope class and `in_use` flag.
        """
        with self._storage.lock:
            if dependency in self._storage.deps:
                provider = self._storage.deps[dependency]
                to_replace = provider.replace(
                    scope_class=(scope_class if override_scope else None),
                    # If the provider is already in use, keep it in use
                    # otherwise, use the new value. For example, if a provider
                    # is already in use and we want to replace it with a resource,
                    # we should keep it in use. If it's already a resource and we
                    # want to replace it with a regular dependency, we should set
                    # is_use to True.
                    in_use=(provider.in_use or in_use),
                )
                if to_replace != provider:
                    self._storage.deps[dependency] = to_replace
            else:
                self._storage.deps[dependency] = Provider.from_dependency(
                    dependency=dependency,
                    scope_class=scope_class,
                    in_use=in_use,
                )

    def get(self, dependency: DependencyCallable) -> Provider:
        with self._storage.lock:
            if self._storage.overrides.get(dependency):
                dependency = self._storage.overrides[dependency]
            return self._storage.deps[dependency]

    def filter(self, predicate: Callable[[Provider], bool]) -> Iterable[Provider]:
        return filter(predicate, self._storage)


class Registry:
    def __init__(
        self, storage: RegistryStorage, internal_registry: InternalRegistry
    ) -> None:
        self._storage = storage
        self._internal_registry = internal_registry

    def override(
        self,
        dependency: DependencyCallable,
        new_dependency: DependencyCallable | None | object = unset,
    ) -> Callable[[DependencyCallable], DependencyCallable]:
        """
        Override a dependency with a new one. It can be used as a decorator,
        as a context manager or as a regular method call. New dependency will be
        added to the registry.
        Examples:
        ```
        @registry.override(get_settings)
        def real_settings():
            return {"real": "settings"}

        with registry.override(get_settings, real_settings):
            ...

        registry.override(get_settings, real_settings)
        registry.override(get_settings, None)  # clear override
        """

        def decorator(override_to: DependencyCallable) -> DependencyCallable:
            self._internal_registry.add(override_to, in_use=True)
            if dependency is override_to:
                raise ValueError("Cannot override a dependency with itself")
            self._storage.overrides[dependency] = override_to
            return override_to

        if new_dependency is unset:
            return decorator

        with self._storage.lock:
            original_dependency = self._storage.overrides.get(dependency)
            if callable(new_dependency):
                decorator(new_dependency)
            else:
                self._storage.overrides.pop(dependency, None)

        @contextmanager
        def manage_context() -> Generator[None, None, None]:
            try:
                yield
            finally:
                self.override(dependency, original_dependency)

        return manage_context()

    def clear(self) -> None:
        """
        Clear the registry. It will remove all dependencies and overrides.
        This method will not close any resources. So you need to manually call
        `shutdown_dependencies` before this method.
        """
        with self._storage.lock:
            self._storage.deps.clear()
            self._storage.overrides.clear()

    def clear_overrides(self) -> None:
        """
        Clear all overrides. It will remove all overrides, but keep the dependencies.
        """
        with self._storage.lock:
            self._storage.overrides.clear()


_registry_storage = RegistryStorage()
_internal_registry = InternalRegistry(_registry_storage)
registry = Registry(_registry_storage, _internal_registry)
_scopes: dict[type[Scope], Scope] = {
    NullScope: NullScope(),
    ParentCallScope: ParentCallScope(),
    SingletonScope: SingletonScope(),
}
_lock = threading.RLock()


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
    _internal_registry.add(dependency)
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
            bound, dep_arguments, scopes = _arguments_to_getters(
                args, kwargs, signature, is_async=True
            )
            for scope in scopes:
                scope.enter_decorator()
            for name, get_value in dep_arguments.items():
                bound.arguments[name] = await get_value()

            result_or_gen = fn(*bound.args, **bound.kwargs)
            if inspect.isasyncgen(result_or_gen):
                result = result_or_gen
            else:
                result = await result_or_gen  # type: ignore[misc]

            for scope in scopes:
                scope.exit_decorator()
                coro = scope.close_local()
                if coro is not None:
                    await coro
            return cast("T", result)

    else:

        @functools.wraps(fn)
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            bound, dep_arguments, scopes = _arguments_to_getters(
                args, kwargs, signature, is_async=False
            )
            for scope in scopes:
                scope.enter_decorator()
            for name, get_value in dep_arguments.items():
                bound.arguments[name] = get_value()

            result = fn(*bound.args, **bound.kwargs)
            for scope in scopes:
                scope.exit_decorator()
                scope.close_local()
            return result

    return wrapper  # type: ignore[return-value]


def dependency(*, scope_class: type[Scope] = NullScope) -> Callable[[TC], TC]:
    """
    Decorator to declare a dependency. You don't need to use it with default arguments,
    use it only if you want to change the scope of the dependency.
    Should be placed last in the decorator chain (on top).
    """

    if scope_class not in _scopes:
        _scopes[scope_class] = scope_class()

    def decorator(fn: TC) -> TC:
        _internal_registry.add(
            fn, scope_class=scope_class, in_use=False, override_scope=True
        )
        return fn

    return decorator


def resource(fn: TC) -> TC:
    """
    Decorator to declare a resource. Resource is a dependency that should be
    called only once, cached and shared across the application.
    On shutdown, all resources will be closed
    (you need to call `shutdown_dependencies` manually).
    Use it with a dependency generator function to declare a resource.
    Should be placed last in the decorator chain (on top).
    """
    return dependency(scope_class=SingletonScope)(fn)


def init_dependencies() -> Awaitable:
    """
    Call this function to close all resources. Usually, it should be called
    when your application is shutting down.
    """
    async_resources = []
    global_providers = _internal_registry.filter(
        lambda p: p.in_use and issubclass(p.scope_class, GlobalScope)
    )
    for provider in global_providers:
        if provider.is_async:
            async_resources.append(_resolve_value_async(provider))
        else:
            _resolve_value(provider)

    if async_resources:
        return asyncio.gather(*async_resources)
    return DummyAwaitable()


def shutdown_dependencies() -> Awaitable:
    """
    Call this function to close all resources. Usually, it should be called
    when your application is shut down.
    """
    tasks = []
    for scope in _scopes.values():
        coro = scope.close_global()
        if coro is not None:
            tasks.append(coro)
    return asyncio.gather(*tasks)


class Dependency(NamedTuple):
    original: DependencyCallable

    def __call__(self) -> Dependency:
        return self

    def get_provider(self) -> Provider:
        return _internal_registry.get(self.original)


@dataclass(frozen=True)
class Provider:
    dependency: DependencyCallable
    is_async: bool
    scope_class: type[Scope]
    in_use: bool

    @classmethod
    def from_dependency(
        cls,
        dependency: DependencyCallable,
        scope_class: type[Scope],
        in_use: bool,
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
) -> tuple[BoundArguments, dict[str, Callable[[], Any]], list[Scope]]:
    bound = signature.bind(*args, **kwargs)
    bound.apply_defaults()
    dependencies: dict[Provider, list[str]] = {}
    for name, value in bound.arguments.items():
        if isinstance(value, Dependency):
            dependencies.setdefault(value.get_provider(), []).append(name)

    get_val = _resolve_value_async if is_async else _resolve_value

    dep_arguments = {}
    scopes = []
    for provider, names in dependencies.items():
        get_value: Callable = functools.partial(get_val, provider)
        for name in names:
            dep_arguments[name] = get_value
        scope = provider.get_scope()
        if scope not in scopes:
            scopes.append(scope)

    return bound, dep_arguments, scopes


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
