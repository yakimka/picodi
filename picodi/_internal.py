from __future__ import annotations

import contextlib
import copy
import functools
import inspect
import threading
from collections.abc import Callable, Iterator
from typing import TYPE_CHECKING, Annotated, Any, get_origin

from picodi._scopes import AutoScope, ScopeType
from picodi._types import DependencyCallable, DependNode, Depends
from picodi.support import ExitStack

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Generator

    from picodi._registry import Provider, Registry, Storage


try:
    import fastapi.params
except ImportError:  # pragma: no cover
    fastapi = None  # type: ignore[assignment] # pragma: no cover


StackItem = tuple[DependNode, Iterator[DependNode], dict[str, Any]]


class _SyncInjectionContext:
    """Context manager for sync dependency injection that handles StopIteration properly."""

    def __init__(
        self,
        dependant: DependNode,
        signature: inspect.Signature,
        registry: Registry,
        args: tuple[Any, ...],
        kwargs: dict[str, Any],
    ) -> None:
        self.gen = wrapper_helper(
            dependant,
            signature,
            is_async=False,
            registry=registry,
            args=args,
            kwargs=kwargs,
        )
        self.user_stop_iteration: StopIteration | None = None

    def __enter__(self) -> Any:
        try:
            value, action = next(self.gen)
            while True:
                if action == "result":
                    return value
                elif action == "user_stop_iteration":
                    # StopIteration from user code - save it to raise in __exit__
                    self.user_stop_iteration = value
                    return None
                try:
                    value, action = self.gen.send(value)
                except StopIteration:
                    return None
                except RuntimeError as e:
                    # PEP 479: StopIteration raised in generator is converted to RuntimeError
                    if e.__cause__ is not None and isinstance(
                        e.__cause__, StopIteration
                    ):
                        self.user_stop_iteration = e.__cause__
                        return None
                    raise
        except BaseException:
            self.gen.close()
            raise

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: Any,
    ) -> None:
        # Continue executing generator for cleanup
        try:
            if (
                exc_val is not None
                and exc_type is not None
                and self.user_stop_iteration is None
            ):
                # If there was an exception in user code, pass it to generator
                self.gen.throw(exc_type, exc_val, exc_tb)
            else:
                # Continue normal execution for cleanup
                try:
                    value, action = self.gen.send(None)
                    # Process remaining yields (cleanup actions)
                    while True:
                        if action == "close_scope":
                            pass  # Scope cleanup
                        try:
                            value, action = self.gen.send(value)
                        except StopIteration:
                            break
                        except RuntimeError as e:
                            # Handle nested StopIteration from cleanup code
                            if e.__cause__ is not None and isinstance(
                                e.__cause__, StopIteration
                            ):
                                break
                            raise
                except StopIteration:
                    pass
        except BaseException:
            self.gen.close()
            raise
        else:
            self.gen.close()

        if self.user_stop_iteration is not None:
            raise self.user_stop_iteration


def sync_injection_context(
    dependant: DependNode,
    signature: inspect.Signature,
    registry: Registry,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> _SyncInjectionContext:
    return _SyncInjectionContext(dependant, signature, registry, args, kwargs)


@contextlib.asynccontextmanager
async def async_injection_context(
    dependant: DependNode,
    signature: inspect.Signature,
    registry: Registry,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> AsyncGenerator[Any]:
    gen = wrapper_helper(
        dependant,
        signature,
        is_async=True,
        registry=registry,
        args=args,
        kwargs=kwargs,
    )
    value, action = next(gen)
    exceptions = []
    user_stop_iteration = None
    while True:
        if inspect.iscoroutine(value):
            try:
                value = await value
            except Exception as e:
                exceptions.append(e)

        if action == "result":
            yield value
        elif action == "user_stop_iteration":
            # StopIteration from user code - save it to raise later
            user_stop_iteration = value
            break
        try:
            value, action = gen.send(value)
        except StopIteration:
            break
        except RuntimeError as e:
            # PEP 479: StopIteration raised in generator is converted to RuntimeError
            if e.__cause__ is not None and isinstance(e.__cause__, StopIteration):
                user_stop_iteration = e.__cause__
                break
            raise
    if exceptions:
        # TODO use `ExceptionGroup` after dropping 3.10 support
        raise exceptions[0]
    gen.close()
    if user_stop_iteration is not None:
        raise user_stop_iteration


def wrapper_helper(
    dependant: DependNode,
    signature: inspect.Signature,
    is_async: bool,
    registry: Registry,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> Generator[Any]:
    exit_stack = ExitStack()
    storage = get_storage_from_registry(registry)
    if _need_patch(dependant, storage):
        dependant = copy.deepcopy(dependant)
        _patch_dependant(dependant, storage)
    bound = signature.bind(*args, **kwargs)
    bound.apply_defaults()
    scopes: set[ScopeType] = set()
    is_root = any(isinstance(value, Depends) for value in bound.arguments.values())

    if is_root:
        stack: list[StackItem] = [(dependant, iter(dependant.dependencies), {})]
        while stack:
            node, deps_iter, dep_kwargs = stack[-1]
            try:
                dep = next(deps_iter)
                stack.append((dep, iter(dep.dependencies), {}))
            except StopIteration:
                if node.name is None:
                    for dep in node.dependencies:
                        assert dep.name is not None
                        if isinstance(bound.arguments.get(dep.name), Depends):
                            bound.arguments[dep.name] = dep_kwargs[dep.name]
                    stack.pop()
                    break

                provider = storage.get(node.value)
                scopes.add(provider.get_scope())
                lazy_call = LazyResolver(
                    provider=provider,
                    kwargs=dep_kwargs,
                    exit_stack=exit_stack,
                    registry=registry,
                    dependant=dependant.value,
                )
                res = yield lazy_call(is_async=is_async), "dependency"
                stack.pop()
                _, _, parent_kwargs = stack[-1]
                parent_kwargs[node.name] = res

    for scope in scopes:
        scope.enter_inject(global_key=dependant.value)

    try:
        result = dependant.value(*bound.args, **bound.kwargs)
    except StopIteration as e:
        # Don't raise StopIteration directly as it causes PEP 479 RuntimeError
        # Instead, pass it through yield to be raised outside the generator
        for scope in scopes:
            scope.exit_inject(e, global_key=dependant.value)
            if isinstance(scope, AutoScope):
                yield exit_stack.close(e), "close_scope"
        yield e, "user_stop_iteration"
        return
    except Exception as e:
        for scope in scopes:
            scope.exit_inject(e, global_key=dependant.value)
            if isinstance(scope, AutoScope):
                yield exit_stack.close(e), "close_scope"
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
                    scope.exit_inject(exception, global_key=dependant.value)
                    if isinstance(scope, AutoScope):
                        exit_stack.close(exception)

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
                    scope.exit_inject(exception, global_key=dependant.value)
                    if isinstance(scope, AutoScope):
                        await exit_stack.close(exception)

        yield gen(), "result"
        return

    yield result, "result"
    for scope in scopes:
        scope.exit_inject(global_key=dependant.value)
        if isinstance(scope, AutoScope):
            yield exit_stack.close(), "close_scope"


def _need_patch(dependant: DependNode, storage: Storage) -> bool:
    if dependant.name is None and not storage.has_overrides():
        return False

    for dep in dependant.dependencies:
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
        *,
        registry: Registry,
        dependant: Callable,
    ) -> None:
        self.provider = provider
        self.kwargs = kwargs or {}
        self.exit_stack = exit_stack
        self.registry = registry
        self.dependant = dependant

    def __call__(self, is_async: bool) -> Any:
        call = self._resolve_async if is_async else self._resolve
        return call()

    def _resolve(self) -> Any:
        scope = self.provider.get_scope()
        try:
            value = scope.get(self.provider.dependency, global_key=self.dependant)
        except KeyError:
            if self.provider.is_async:
                value = self.provider.dependency()
            else:
                with lock:
                    try:
                        value = scope.get(
                            self.provider.dependency, global_key=self.dependant
                        )
                    except KeyError:
                        value = self.provider.resolve_value(
                            self.exit_stack,
                            registry=self.registry,
                            dependant=self.dependant,
                            kwargs=self.kwargs,
                        )
                        scope.set(
                            self.provider.dependency, value, global_key=self.dependant
                        )
        return value

    async def _resolve_async(self) -> Any:
        scope = self.provider.get_scope()
        try:
            value = scope.get(self.provider.dependency, global_key=self.dependant)
        except KeyError:
            with lock:
                try:
                    value = scope.get(
                        self.provider.dependency, global_key=self.dependant
                    )
                except KeyError:
                    value = self.provider.resolve_value(
                        self.exit_stack,
                        registry=self.registry,
                        dependant=self.dependant,
                        kwargs=self.kwargs,
                    )
                    if self.provider.is_async:
                        value = await value
                    scope.set(
                        self.provider.dependency, value, global_key=self.dependant
                    )
        return value


lock = threading.RLock()


def get_storage_from_registry(registry: Registry) -> Storage:
    return registry._storage  # noqa: SLF001
