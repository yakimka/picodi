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
_resources: dict[Dependency, AsyncContextManager | ContextManager] = {}
_resources_result_cache: dict[Dependency, Any] = {}


def Depends(dependency: Dependency, /, use_cache: bool = True) -> Any:  # noqa: N802
    if dependency in _resources and not use_cache:
        raise ValueError("use_cache=False is not supported for resources")
    return _Depends(dependency, use_cache)


@dataclass(frozen=True)
class _Depends:
    dependency: Dependency
    use_cache: bool


T = TypeVar("T")
P = ParamSpec("P")


@dataclass(frozen=True)
class ResolvedDependency:
    original: Dependency
    context_manager: ContextManager | AsyncContextManager | None = field(compare=False)
    is_async: bool = field(default=False, compare=False)
    use_cache: bool = True

    @classmethod
    def resolve(cls, depends: _Depends) -> ResolvedDependency:
        context_manager: ContextManager | AsyncContextManager | None = None
        is_async = False
        if inspect.isasyncgenfunction(depends.dependency):
            context_manager = asynccontextmanager(depends.dependency)()
            is_async = True
        elif inspect.isgeneratorfunction(depends.dependency):
            context_manager = contextmanager(depends.dependency)()
        return cls(depends.dependency, context_manager, is_async, depends.use_cache)


TC = TypeVar("TC", bound=Callable)


def resource(fn: TC) -> TC:
    manager: ContextManager | AsyncContextManager
    if inspect.isasyncgenfunction(fn):
        manager = asynccontextmanager(fn)()
    elif inspect.isgeneratorfunction(fn):
        manager = contextmanager(fn)()
    else:
        raise ValueError("Resource must be a generator or async generator function")
    _resources[fn] = manager
    _resources_result_cache[fn] = _unset

    return fn


def inject(fn: Callable[P, T]) -> Callable[P, T | Coroutine[Any, Any, T]]:
    signature = inspect.signature(fn)

    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        bound = signature.bind(*args, **kwargs)
        bound.apply_defaults()

        dependencies: dict[ResolvedDependency, list[str]] = {}
        for name, value in bound.arguments.items():
            if isinstance(value, _Depends):
                dependencies.setdefault(ResolvedDependency.resolve(value), []).append(
                    name
                )

        with _call_dependencies(dependencies) as arguments:
            bound.arguments.update(arguments)
            return fn(*bound.args, **bound.kwargs)

    return wrapper


def shutdown_resources() -> None:
    _resources_exit_stack.close()


@contextmanager
def _call_dependencies(
    dependencies: dict[ResolvedDependency, list[str]],
) -> Generator[dict[str, Any], None, None]:
    managers: list[tuple[AbstractContextManager, list[str]]] = []
    async_managers: list[tuple[AbstractAsyncContextManager, list[str]]] = []
    results = {}
    for dependency, names in dependencies.items():
        if context_manager := _resources.get(dependency.original):
            if isinstance(context_manager, AbstractContextManager):
                if _resources_result_cache.get(dependency.original) is _unset:
                    result = _resources_exit_stack.enter_context(context_manager)
                    _resources_result_cache[dependency.original] = result

                result = _resources_result_cache[dependency.original]
                results.update({name: result for name in names})
        elif dependency.context_manager:
            if isinstance(dependency.context_manager, AbstractAsyncContextManager):
                async_managers.append((dependency.context_manager, names))
            else:
                managers.append((dependency.context_manager, names))
        else:
            if dependency.use_cache:
                result = dependency.original()
                results.update({name: result for name in names})
            else:
                results.update({name: dependency.original() for name in names})

    with ExitStack() as stack:
        values = {manager: stack.enter_context(manager) for manager, _ in managers}
        for manager, names in managers:
            for name in names:
                results[name] = values[manager]
        yield results
