from __future__ import annotations

import functools
import inspect
from collections.abc import Callable, Coroutine, Generator
from contextlib import (
    AbstractAsyncContextManager,
    AbstractContextManager,
    ExitStack,
    asynccontextmanager,
    contextmanager,
)
from dataclasses import dataclass, field
from typing import Any, AsyncContextManager, ContextManager, ParamSpec, TypeVar

Dependency = Callable[..., Any]


_unset = object()
_resources_exit_stack = ExitStack()
_resources_result_cache: dict[Dependency, Any] = {}
T = TypeVar("T")
P = ParamSpec("P")
TC = TypeVar("TC", bound=Callable)


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
    if getattr(dependency, "_scope_", None) and not use_cache:
        raise ValueError("use_cache=False is not supported for resources")
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

    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        bound = signature.bind(*args, **kwargs)
        bound.apply_defaults()

        dependencies: dict[Depends, list[str]] = {}
        for name, value in bound.arguments.items():
            if isinstance(value, Depends):
                dependencies.setdefault(value, []).append(name)

        with _call_dependencies(dependencies) as arguments:
            bound.arguments.update(arguments)
            return fn(*bound.args, **bound.kwargs)

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
    _resources_exit_stack.close()


@dataclass(frozen=True)
class Depends:
    dependency: Dependency
    use_cache: bool
    context_manager: ContextManager | AsyncContextManager | None = field(compare=False)
    is_async: bool = field(compare=False)

    @classmethod
    def from_dependency(cls, dependency: Dependency, use_cache: bool) -> Depends:
        context_manager: ContextManager | AsyncContextManager | None = None
        is_async = False
        if inspect.isasyncgenfunction(dependency):
            context_manager = asynccontextmanager(dependency)()
            is_async = True
        elif inspect.isgeneratorfunction(dependency):
            context_manager = contextmanager(dependency)()

        if getattr(dependency, "_scope_", None):
            _resources_result_cache[dependency] = _unset
        return cls(dependency, use_cache, context_manager, is_async)


@contextmanager
def _call_dependencies(
    depends_items: dict[Depends, list[str]],
) -> Generator[dict[str, Any], None, None]:
    managers: list[tuple[AbstractContextManager, list[str]]] = []
    async_managers: list[tuple[AbstractAsyncContextManager, list[str]]] = []
    results = {}
    for depends, names in depends_items.items():
        if getattr(depends.dependency, "_scope_", None):
            if isinstance(depends.context_manager, AbstractContextManager):
                if _resources_result_cache.get(depends.dependency) is _unset:
                    result = _resources_exit_stack.enter_context(
                        depends.context_manager
                    )
                    _resources_result_cache[depends.dependency] = result

                result = _resources_result_cache[depends.dependency]
                results.update({name: result for name in names})
        elif depends.context_manager:
            if isinstance(depends.context_manager, AbstractAsyncContextManager):
                async_managers.append((depends.context_manager, names))
            else:
                managers.append((depends.context_manager, names))
        else:
            if depends.use_cache:
                result = depends.dependency()
                results.update({name: result for name in names})
            else:
                results.update({name: depends.dependency() for name in names})

    with ExitStack() as stack:
        values = {manager: stack.enter_context(manager) for manager, _ in managers}
        for manager, names in managers:
            for name in names:
                results[name] = values[manager]
        yield results
