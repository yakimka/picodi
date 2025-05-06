from __future__ import annotations

import copy
import functools
import inspect
import threading
from typing import TYPE_CHECKING, Annotated, Any, get_origin

from picodi._scopes import AutoScope, ScopeType
from picodi._types import DependencyCallable, DependNode, Depends
from picodi.support import ExitStack

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

    from picodi._state import Provider, Storage


try:
    import fastapi.params
except ImportError:  # pragma: no cover
    fastapi = None  # type: ignore[assignment] # pragma: no cover


def wrapper_helper(
    dependant: DependNode,
    signature: inspect.Signature,
    is_async: bool,
    storage: Storage,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> Generator[Any]:
    exit_stack = ExitStack()
    if _need_patch(dependant, storage):
        dependant = copy.deepcopy(dependant)
        _patch_dependant(dependant, storage)
    bound = signature.bind(*args, **kwargs)
    bound.apply_defaults()
    arguments: dict[str, Any] = bound.arguments
    scopes: list[ScopeType] = []
    is_root = any(isinstance(value, Depends) for value in arguments.values())

    if is_root:
        excluded_args = [
            name for name, value in arguments.items() if not isinstance(value, Depends)
        ]
        arguments, scopes = _resolve_dependencies(
            dependant, exit_stack, storage, exclude=excluded_args
        )

    for scope in scopes:
        scope.enter_inject()
    for name, call in arguments.items():
        if isinstance(call, LazyResolver):
            value = yield call(is_async=is_async), "dependency"
            bound.arguments[name] = value

    try:
        result = dependant.value(*bound.args, **bound.kwargs)
    except Exception as e:
        for scope in scopes:
            scope.exit_inject(e)
            if isinstance(scope, AutoScope):
                yield scope.shutdown(exit_stack, e), "close_scope"
        raise

    if inspect.isgenerator(result):

        @functools.wraps(result)  # type: ignore[arg-type]
        def gen() -> Generator[Any]:
            exception = None
            try:
                yield from result
            except Exception as e:
                exception = e
                raise
            finally:
                for scope in scopes:
                    scope.exit_inject(exception)
                    if isinstance(scope, AutoScope):
                        scope.shutdown(exit_stack, exception)

        yield gen(), "result"
        return
    elif inspect.isasyncgen(result):

        @functools.wraps(result)  # type: ignore[arg-type]
        async def gen() -> AsyncGenerator[Any]:
            exception = None
            try:
                async for item in result:
                    yield item
            except Exception as e:
                exception = e
                raise
            # TODO use
            #   https://flake8-async.readthedocs.io/en/latest/glossary.html#cancel-scope
            #   https://docs.python.org/3/library/asyncio-task.html#task-cancellation
            finally:
                for scope in scopes:
                    scope.exit_inject(exception)
                    if isinstance(scope, AutoScope):
                        await scope.shutdown(exit_stack, exception)

        yield gen(), "result"
        return

    yield result, "result"
    for scope in scopes:
        scope.exit_inject()
        if isinstance(scope, AutoScope):
            yield scope.shutdown(exit_stack), "close_scope"


def _need_patch(dependant: DependNode, storage: Storage) -> bool:
    if dependant.name is None and not storage.has_overrides():
        return False

    for dep in dependant.dependencies:  # noqa: SIM110
        if _need_patch(dep, storage):
            return True

    return bool(dependant.name and storage.get_override(dependant.value))


def _patch_dependant(dependant: DependNode, storage: Storage) -> None:
    for dep in dependant.dependencies:
        _patch_dependant(dep, storage)

    if dependant.name is None:
        return

    if override := storage.get_override(dependant.value):
        dependant.value = override
        override_tree = build_depend_tree(dependant.value, storage=storage)
        dependant.dependencies = override_tree.dependencies


def _resolve_dependencies(
    dependant: DependNode,
    exit_stack: ExitStack,
    storage: Storage,
    exclude: list[str] | None = None,
) -> tuple[dict[str, LazyResolver], list[ScopeType]]:
    scopes = set()
    resolved_dependencies = {}
    for dep in dependant.dependencies:
        if exclude and dep.name in exclude:
            continue
        values, dep_scopes = _resolve_dependencies(dep, exit_stack, storage)
        resolved_dependencies.update(values)
        scopes.update(dep_scopes)

    if dependant.name is None:
        return resolved_dependencies, list(scopes)

    provider = storage.get(dependant.value)
    value = LazyResolver(
        provider=provider,
        kwargs=resolved_dependencies,
        exit_stack=exit_stack,
    )
    return {dependant.name: value}, [provider.get_scope()]


def build_depend_tree(
    dependency: DependencyCallable, *, name: str | None = None, storage: Storage
) -> DependNode:
    signature = inspect.signature(dependency)
    dependencies = []
    for name_, value in signature.parameters.items():
        param_dep = _extract_and_register_dependency_from_parameter(
            value,
            storage,
        )
        if param_dep is not None:
            dependencies.append(
                build_depend_tree(param_dep, name=name_, storage=storage)
            )
    return DependNode(value=dependency, dependencies=dependencies, name=name)


def _extract_and_register_dependency_from_parameter(
    value: inspect.Parameter, storage: Storage
) -> DependencyCallable | None:
    if isinstance(value.default, Depends):
        storage.add(value.default.call)
        return value.default.call

    if fastapi is None:
        return None  # type: ignore[unreachable]  # pragma: no cover
    fastapi_dependency = None
    if isinstance(value.default, fastapi.params.Depends):
        fastapi_dependency = value.default.dependency
    elif get_origin(value.annotation) is Annotated:
        for metadata in value.annotation.__metadata__:
            if isinstance(metadata, fastapi.params.Depends):
                fastapi_dependency = metadata.dependency
                break
    if isinstance(fastapi_dependency, Depends):
        storage.add(fastapi_dependency.call)  # type: ignore[unreachable]
        return fastapi_dependency.call
    return None


class LazyResolver:
    def __init__(
        self,
        provider: Provider,
        kwargs: dict[str, Any] | None = None,
        exit_stack: ExitStack | None = None,
    ) -> None:
        self.provider = provider
        self.kwargs = kwargs or {}
        self.exit_stack = exit_stack

    def __call__(self, is_async: bool) -> Any:
        call = self._resolve_async if is_async else self._resolve
        return call()

    def _resolve(self) -> Any:
        scope = self.provider.get_scope()
        try:
            value = scope.get(self.provider.dependency)
        except KeyError:
            if self.provider.is_async:
                value = self.provider.dependency()
            else:
                with lock:
                    try:
                        value = scope.get(self.provider.dependency)
                    except KeyError:
                        value = self.provider.resolve_value(
                            self.exit_stack, **self.kwargs
                        )
                        scope.set(self.provider.dependency, value)
        return value

    async def _resolve_async(self) -> Any:
        scope = self.provider.get_scope()
        try:
            value = scope.get(self.provider.dependency)
        except KeyError:
            with lock:
                try:
                    value = scope.get(self.provider.dependency)
                except KeyError:
                    value = self.provider.resolve_value(self.exit_stack, **self.kwargs)
                    if self.provider.is_async:
                        value = await value
                    scope.set(self.provider.dependency, value)
        return value


lock = threading.RLock()
