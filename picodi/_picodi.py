from __future__ import annotations

import asyncio
import functools
import inspect
import logging
import threading
from collections.abc import (
    AsyncGenerator,
    Awaitable,
    Callable,
    Generator,
    Iterable,
    Iterator,
)
from contextlib import asynccontextmanager, contextmanager
from dataclasses import asdict, dataclass
from typing import (
    Annotated,
    Any,
    ContextManager,
    NamedTuple,
    ParamSpec,
    TypeVar,
    cast,
    get_origin,
    overload,
)

from picodi._scopes import (
    AutoScope,
    ContextVarScope,
    ManualScope,
    NullScope,
    ScopeType,
    SingletonScope,
)
from picodi.support import ExitStack, NullAwaitable

try:
    import fastapi.params
except ImportError:  # pragma: no cover
    fastapi = None  # type: ignore[assignment] # pragma: no cover


logger = logging.getLogger("picodi")


DependencyCallable = Callable[..., Any]
LifespanScopeClass = type[ManualScope] | tuple[type[ManualScope], ...]
Tags = list[str] | tuple[str, ...]
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
        scope_class: type[ScopeType] = NullScope,
        override_scope: bool = False,
        tags: Tags = (),
    ) -> None:
        """
        Add a dependency to the registry.
        """
        with self._storage.lock:
            if dependency in self._storage.deps:
                provider = self._storage.deps[dependency]
                to_replace = provider.replace(
                    scope_class=(scope_class if override_scope else None)
                )
                if to_replace != provider:
                    self._storage.deps[dependency] = to_replace
            else:
                self._storage.deps[dependency] = Provider.from_dependency(
                    dependency=dependency,
                    scope_class=scope_class,
                    tags=tags,
                )

    def get(self, dependency: DependencyCallable) -> Provider:
        with self._storage.lock:
            dependency = self.get_dep_or_override(dependency)
            return self._storage.deps[dependency]

    def get_dep_or_override(self, dependency: DependencyCallable) -> DependencyCallable:
        return self._storage.overrides.get(dependency, dependency)

    def filter(self, predicate: Callable[[Provider], bool]) -> Iterable[Provider]:
        return filter(predicate, self._storage)


class Registry:
    """
    Manages dependencies and overrides.
    """

    def __init__(
        self, storage: RegistryStorage, internal_registry: InternalRegistry
    ) -> None:
        self._storage = storage
        self._internal_registry = internal_registry

    @overload
    def override(
        self, dependency: DependencyCallable, new_dependency: None = None
    ) -> Callable[[DependencyCallable], DependencyCallable]: ...

    @overload
    def override(
        self, dependency: DependencyCallable, new_dependency: DependencyCallable
    ) -> ContextManager[None]: ...

    def override(
        self,
        dependency: DependencyCallable,
        new_dependency: DependencyCallable | None | object = unset,
    ) -> Callable[[DependencyCallable], DependencyCallable] | ContextManager[None]:
        """
        Override a dependency with a new one. It can be used as a decorator,
        as a context manager or as a regular method call. New dependency will be
        added to the registry.

        :param dependency: dependency to override
        :param new_dependency: new dependency to use. If explicitly set to ``None``,
            it will remove the override.

        Examples
        --------
        .. code-block:: python

            @registry.override(get_settings)
            def real_settings():
                return {"real": "settings"}


            with registry.override(get_settings, real_settings):
                ...

            registry.override(get_settings, real_settings)
            registry.override(get_settings, None)  # clear override
        """

        def decorator(override_to: DependencyCallable) -> DependencyCallable:
            self._internal_registry.add(override_to)
            if dependency is override_to:
                raise ValueError("Cannot override a dependency with itself")
            self._storage.overrides[dependency] = override_to
            return override_to

        if new_dependency is unset:
            return decorator

        with self._storage.lock:
            call_dependency = self._storage.overrides.get(dependency)
            if callable(new_dependency):
                decorator(new_dependency)
            else:
                self._storage.overrides.pop(dependency, None)

        @contextmanager
        def manage_context() -> Generator[None, None, None]:
            try:
                yield
            finally:
                self.override(dependency, call_dependency)

        return manage_context()

    def clear_overrides(self) -> None:
        """
        Clear all overrides. It will remove all overrides, but keep the dependencies.
        """
        with self._storage.lock:
            self._storage.overrides.clear()

    def clear(self) -> None:
        """
        Clear the registry. It will remove all dependencies and overrides.
        This method will not close any dependencies. So you need to manually call
        :func:`shutdown_dependencies` before this method.
        """
        with self._storage.lock:
            self._storage.deps.clear()
            self._storage.overrides.clear()


_registry_storage = RegistryStorage()
_internal_registry = InternalRegistry(_registry_storage)
registry = Registry(_registry_storage, _internal_registry)
_scopes: dict[type[ScopeType], ScopeType] = {
    NullScope: NullScope(),
    SingletonScope: SingletonScope(),
    ContextVarScope: ContextVarScope(),
}
_lock = threading.RLock()


def Provide(dependency: DependencyCallable, /) -> Any:  # noqa: N802
    """
    Declare a provider.
    It takes a single "dependency" callable (like a function).
    Don't call it directly, picodi will call it for you.

    :param dependency: can be a regular function or a generator with one yield.
        If the dependency is a generator, it will be used as a context manager.
        Any generator that is valid for :func:`python:contextlib.contextmanager`
        can be used as a dependency.

    Example
    -------
    .. code-block:: python

        from picodi import Provide, inject


        def get_db():
            yield "db connection"
            print("closing db connection")


        @inject
        def my_service(db: str = Provide(get_db)):
            assert db == "db connection"
    """
    return Depends(dependency)


def inject(fn: Callable[P, T]) -> Callable[P, T]:
    """
    Decorator to inject dependencies into a function.
    Use it in combination with :func:`Provide` to declare dependencies.
    Should be placed first in the decorator chain (on bottom).

    :param fn: function to decorate.

    Example
    -------
    .. code-block:: python

        from picodi import inject, Provide


        @inject
        def my_service(db=Provide(some_dependency_func)): ...
    """
    signature = inspect.signature(fn)
    dependant = _build_depend_tree(Depends(fn))

    if inspect.iscoroutinefunction(fn) or inspect.isasyncgenfunction(fn):

        @functools.wraps(fn)
        async def fun_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            gen = _wrapper_helper(
                dependant,
                signature,
                is_async=True,
                args=args,
                kwargs=kwargs,
            )
            value, action = next(gen)
            result = None
            exceptions = []
            while True:
                if inspect.iscoroutine(value):
                    try:
                        value = await value
                    except Exception as e:  # noqa: PIE786
                        exceptions.append(e)

                if action == "result":
                    result = value
                try:
                    value, action = gen.send(value)
                except StopIteration:
                    break
            if exceptions:
                # TODO use `ExceptionGroup` after dropping 3.10 support
                raise exceptions[0]
            return cast("T", result)

        wrapper = fun_wrapper

        if inspect.isasyncgenfunction(fn):

            @functools.wraps(fn)
            async def gen_wrapper(
                *args: P.args, **kwargs: P.kwargs
            ) -> AsyncGenerator[T, None]:
                result = await fun_wrapper(*args, **kwargs)
                async for value in result:  # type: ignore[attr-defined]
                    try:
                        yield value
                    except Exception as e:  # noqa: PIE786
                        try:
                            await result.athrow(e)  # type: ignore[attr-defined]
                        except StopAsyncIteration:
                            break

            wrapper = gen_wrapper  # type: ignore[assignment]

    else:

        @functools.wraps(fn)
        def fun_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            gen = _wrapper_helper(
                dependant,
                signature,
                is_async=False,
                args=args,
                kwargs=kwargs,
            )
            value, action = next(gen)
            result = None
            while True:
                if action == "result":
                    result = value
                try:
                    value, action = gen.send(value)
                except StopIteration:
                    break
            return cast("T", result)

        wrapper = fun_wrapper

        if inspect.isgeneratorfunction(fn):

            @functools.wraps(fn)
            def gen_wrapper(
                *args: P.args, **kwargs: P.kwargs
            ) -> Generator[T, None, None]:
                yield from fun_wrapper(*args, **kwargs)  # type: ignore[misc]

            wrapper = gen_wrapper  # type: ignore[assignment]

    return wrapper  # type: ignore[return-value]


def dependency(
    *,
    scope_class: type[ScopeType] = NullScope,
    tags: Tags = (),
) -> Callable[[TC], TC]:
    """
    Decorator to declare a dependency. You don't need to use it with default arguments,
    use it only if you want to change the scope of the dependency.
    Should be placed last in the decorator chain (on top).

    :param scope_class: specify the scope class to use for the dependency. Default is
        :class:`NullScope`.
        Picodi additionally provides a few built-in scopes:
        :class:`SingletonScope`, :class:`ContextVarScope`.
    :param tags: list of tags to assign to the dependency. Tags can be used to select
        which dependencies to initialize. They can be used to group
        dependencies and control their lifecycle.
    """

    if scope_class not in _scopes:
        _scopes[scope_class] = scope_class()

    def decorator(fn: TC) -> TC:
        _internal_registry.add(
            fn,
            scope_class=scope_class,
            override_scope=True,
            tags=tags,
        )
        return fn

    return decorator


def init_dependencies(
    scope_class: LifespanScopeClass = SingletonScope,
    tags: Tags = (),
) -> Awaitable:
    """
    Call this function to close dependencies. Usually, it should be called
    when your application is starting up.

    This function works both for synchronous and asynchronous dependencies.
    If you call it without ``await``, it will initialize only sync dependencies.
    If you call it ``await init_dependencies()``, it will initialize both sync and async
    dependencies.

    If you not pass any arguments, it will initialize only :class:`SingletonScope`
    and its subclasses.

    If you pass tags with scope_class ``and`` logic will be applied.

    :param scope_class: you can specify the scope class to initialize. If passed -
        only dependencies of this scope class and its subclasses will be initialized.
    :param tags: you can specify the dependencies to initialize by tags. If passed -
        only dependencies of this tags will be initialized. If you pass a tag with a
        minus sign, it will exclude dependencies with this tag.
    """
    filtered_providers = _internal_registry.filter(
        lambda p: p.match_tags(tags) and issubclass(p.scope_class, scope_class)
    )
    async_deps = []
    for provider in filtered_providers:
        resolver = LazyResolver(provider)
        value = resolver(provider.is_async)
        if provider.is_async:
            async_deps.append(value)

    if async_deps:
        # asyncio.gather runs coros in different tasks with different context
        #   we can run them in current context with contextvars.copy_context()
        #   but in this case `ContextVarScope` will save values in the wrong context.
        #   So we fix it in dirty way by running all coros one by one until
        #   come up with better solution.
        async def init_all() -> None:
            for dep in async_deps:
                await dep

        return init_all()
    return NullAwaitable()


def shutdown_dependencies(
    scope_class: LifespanScopeClass = ManualScope,
) -> Awaitable:
    """
    Call this function to close dependencies. Usually, it should be called
    when your application is shut down.

    This function works both for synchronous and asynchronous dependencies.
    If you call it without ``await``, it will shutdown only sync dependencies.
    If you call it ``await shutdown_dependencies()``, it will shutdown both
    sync and async dependencies.

    If you not pass any arguments, it will shutdown subclasses of :class:`ManualScope`.

    :param scope_class: you can specify the scope class to shutdown. If passed -
        only dependencies of this scope class and its subclasses will be shutdown.
    """
    tasks = [
        instance.shutdown()  # type: ignore[call-arg]
        for klass, instance in _scopes.items()
        if issubclass(klass, scope_class)
    ]
    if all(isinstance(task, NullAwaitable) for task in tasks):
        return NullAwaitable()
    return asyncio.gather(*tasks)


class Depends(NamedTuple):
    call: DependencyCallable


@dataclass(frozen=True)
class Provider:
    dependency: DependencyCallable
    is_async: bool
    scope_class: type[ScopeType]
    tags: set[str]

    @classmethod
    def from_dependency(
        cls,
        dependency: DependencyCallable,
        scope_class: type[ScopeType],
        tags: Tags,
    ) -> Provider:
        is_async = inspect.iscoroutinefunction(
            dependency
        ) or inspect.isasyncgenfunction(dependency)

        return cls(
            dependency=dependency,
            is_async=is_async,
            scope_class=scope_class,
            tags=set(tags),
        )

    def match_tags(self, tags: Tags) -> bool:
        include_tags = {tag for tag in tags if not tag.startswith("-")}
        exclude_tags = {tag[1:] for tag in tags if tag.startswith("-")}

        if exclude_tags.intersection(self.tags):
            return False

        return bool(not include_tags or include_tags.intersection(self.tags))

    def replace(self, scope_class: type[ScopeType] | None = None) -> Provider:
        kwargs = asdict(self)
        if scope_class is not None:
            kwargs["scope_class"] = scope_class
        return Provider(**kwargs)

    def get_scope(self) -> ScopeType:
        return _scopes[self.scope_class]

    def resolve_value(self, exit_stack: ExitStack | None, **kwargs: Any) -> Any:
        scope = self.get_scope()
        value_or_gen = self.dependency(**kwargs)
        if self.is_async:

            async def resolve_value_inner() -> Any:
                value_or_gen_ = value_or_gen
                if inspect.iscoroutine(value_or_gen):
                    value_or_gen_ = await value_or_gen_
                if inspect.isasyncgen(value_or_gen_):
                    context_manager = asynccontextmanager(
                        lambda *args, **kwargs: value_or_gen_
                    )
                    if isinstance(scope, AutoScope):
                        assert exit_stack is not None, "exit_stack is required"
                        return await scope.enter(exit_stack, context_manager())
                    return await scope.enter(context_manager())
                return value_or_gen_

            return resolve_value_inner()

        if inspect.isgenerator(value_or_gen):
            context_manager = contextmanager(lambda *args, **kwargs: value_or_gen)
            if isinstance(scope, AutoScope):
                assert exit_stack is not None, "exit_stack is required"
                return scope.enter(exit_stack, context_manager())
            return scope.enter(context_manager())
        return value_or_gen


def _wrapper_helper(
    dependant: DependNode,
    signature: inspect.Signature,
    is_async: bool,
    args: tuple[Any, ...],
    kwargs: dict[str, Any],
) -> Generator[Any, None, None]:
    exit_stack = ExitStack()
    bound = signature.bind(*args, **kwargs)
    bound.apply_defaults()
    arguments: dict[str, Any] = bound.arguments
    scopes: list[ScopeType] = []
    is_root = any(isinstance(value, Depends) for value in bound.arguments.values())

    if is_root:
        arguments, scopes = _resolve_dependencies(dependant, exit_stack)

    for scope in scopes:
        scope.enter_inject()
    for name, call in arguments.items():
        if isinstance(call, LazyResolver):
            value = yield call(is_async=is_async), "dependency"
            bound.arguments[name] = value

    try:
        result = dependant.value.call(*bound.args, **bound.kwargs)
    except Exception as e:
        for scope in scopes:
            scope.exit_inject(e)
            if isinstance(scope, AutoScope):
                yield scope.shutdown(exit_stack, e), "close_scope"
        raise

    if inspect.isgenerator(result):

        @functools.wraps(result)  # type: ignore[arg-type]
        def gen() -> Generator[Any, None, None]:
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
        async def gen() -> AsyncGenerator[Any, None]:
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
                        await scope.shutdown(exit_stack, exception)  # noqa: ASYNC102

        yield gen(), "result"
        return

    yield result, "result"
    for scope in scopes:
        scope.exit_inject()
        if isinstance(scope, AutoScope):
            yield scope.shutdown(exit_stack), "close_scope"


def _resolve_dependencies(
    dependant: DependNode, exit_stack: ExitStack
) -> tuple[dict[str, LazyResolver], list[ScopeType]]:
    scopes = set()
    resolved_dependencies = {}
    for dep in dependant.dependencies:
        values, dep_scopes = _resolve_dependencies(dep, exit_stack)
        resolved_dependencies.update(values)
        scopes.update(dep_scopes)

    if dependant.name is None:
        return resolved_dependencies, list(scopes)

    provider = _internal_registry.get(dependant.value.call)
    value = LazyResolver(
        provider=provider,
        kwargs=resolved_dependencies,
        exit_stack=exit_stack,
    )
    return {dependant.name: value}, [provider.get_scope()]


@dataclass
class DependNode:
    value: Depends
    name: str | None
    dependencies: list[DependNode]


def _build_depend_tree(dependency: Depends, name: str | None = None) -> DependNode:
    signature = inspect.signature(dependency.call)
    dependencies = []
    for name_, value in signature.parameters.items():
        param_dep = _extract_and_register_dependency_from_parameter(value)
        if param_dep is not None:
            dependencies.append(_build_depend_tree(param_dep, name=name_))
    return DependNode(value=dependency, dependencies=dependencies, name=name)


def _extract_and_register_dependency_from_parameter(
    value: inspect.Parameter,
) -> Depends | None:
    if isinstance(value.default, Depends):
        _internal_registry.add(value.default.call)
        return value.default

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
        _internal_registry.add(fastapi_dependency.call)  # type: ignore[unreachable]
        return fastapi_dependency
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
                with _lock:
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
            with _lock:
                try:
                    value = scope.get(self.provider.dependency)
                except KeyError:
                    value = self.provider.resolve_value(self.exit_stack, **self.kwargs)
                    if self.provider.is_async:
                        value = await value
                    scope.set(self.provider.dependency, value)
        return value
