from __future__ import annotations

import asyncio
import inspect
import threading
from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
from contextlib import (
    _AsyncGeneratorContextManager,
    _GeneratorContextManager,
    asynccontextmanager,
    contextmanager,
)
from dataclasses import dataclass
from typing import Any, AsyncContextManager, ContextManager, Literal, TypeVar, overload

from picodi._internal import (
    async_injection_context,
    build_depend_tree,
    sync_injection_context,
)
from picodi._scopes import AutoScope, ManualScope, NullScope, ScopeType
from picodi._types import (
    DependencyCallable,
    DependNode,
    Depends,
    InitDependencies,
    LifespanScopeClass,
)
from picodi.support import (
    ExitStack,
    NullAwaitable,
    call_cm_async,
    call_cm_sync,
    is_async_function,
)

TC = TypeVar("TC", bound=Callable)


class Storage:
    def __init__(self) -> None:
        self.deps: dict[DependencyCallable, Provider] = {}
        self.overrides: dict[DependencyCallable, DependencyCallable] = {}
        self.touched_dependencies: set[DependencyCallable] = set()
        self.scopes: dict[type[ScopeType], ScopeType] = {}

    def add(
        self,
        dependency: DependencyCallable,
        scope_class: type[ScopeType] = NullScope,
        override: bool = False,
    ) -> None:
        with lock:
            if scope_class not in self.scopes:
                self.scopes[scope_class] = scope_class()

            if dependency not in self.deps or override:
                self.deps[dependency] = Provider.from_dependency(
                    dependency=dependency,
                    scope=self.scopes[scope_class],
                )

    def get(self, dependency: DependencyCallable) -> Provider:
        dependency = self.get_dep_or_override(dependency)
        self.touched_dependencies.add(dependency)
        if dependency not in self.deps:
            self.add(dependency)
        return self.deps[dependency]

    def get_dep_or_override(self, dependency: DependencyCallable) -> DependencyCallable:
        return self.overrides.get(dependency, dependency)

    def get_override(self, dependency: DependencyCallable) -> DependencyCallable | None:
        return self.overrides.get(dependency)

    def get_original(self, override: DependencyCallable) -> DependencyCallable | None:
        for original, overriden in self.overrides.items():
            if overriden == override:
                return original
        return None

    def has_overrides(self) -> bool:
        return bool(self.overrides)

    @overload
    def resolve(
        self,
        dependencies: list[DependencyCallable],
        registry: Registry,
        is_async: Literal[False],
    ) -> ContextManager:
        """
        Return sync context manager that will return tuple of results
        """

    @overload
    def resolve(
        self,
        dependencies: list[DependencyCallable],
        registry: Registry,
        is_async: Literal[True],
    ) -> AsyncContextManager:
        """
        Return async context manager that will return tuple of results
        """

    def resolve(
        self, dependencies: list[DependencyCallable], registry: Registry, is_async: bool
    ) -> AsyncContextManager | ContextManager:
        signature = inspect.Signature(
            parameters=[
                inspect.Parameter(
                    f"dep{i}",
                    inspect.Parameter.POSITIONAL_ONLY,
                    default=Depends(dep),
                )
                for i, dep in enumerate(dependencies, start=1)
            ],
        )
        dependant = DependNode(
            value=lambda *args: args if len(args) > 1 else args[0],
            name=None,
            dependencies=[
                build_depend_tree(dep, name=f"dep{i}", storage=self)
                for i, dep in enumerate(dependencies, start=1)
            ],
        )
        resolver = async_injection_context if is_async else sync_injection_context
        return resolver(
            dependant,
            signature,
            registry,
            args=(),
            kwargs={},
        )


class Registry:
    """
    Manages dependencies and overrides.
    """

    def __init__(self, for_init: InitDependencies | None = None) -> None:
        self._storage = Storage()
        self._for_init: list[InitDependencies] = [for_init] if for_init else []

    def add(
        self,
        dependency: DependencyCallable,
        scope_class: type[ScopeType] = NullScope,
    ) -> None:
        """
        Add a dependency to the registry and set scope_class for it.
        """
        self._storage.add(dependency, scope_class, override=True)

    def add_for_init(self, dependencies: InitDependencies) -> None:
        """
        Add a dependencies to the list of dependencies to initialize.
        """
        if dependencies not in self._for_init:
            self._for_init.append(dependencies)

    def set_scope(
        self, scope_class: type[ScopeType], *, auto_init: bool = False
    ) -> Callable[[TC], TC]:
        """
        Decorator to declare a dependency.
        Should be placed last in the decorator chain (on top).

        :param scope_class: specify the scope class to use it for the dependency.
        :param auto_init: if set to ``True``, the dependency will be added to the list
            of dependencies to initialize. This is useful for dependencies that
            need to be initialized before the application starts.
        """

        def decorator(fn: TC) -> TC:
            self._storage.add(
                fn,
                scope_class=scope_class,
                override=True,
            )
            if auto_init:
                self.add_for_init([fn])
            return fn

        return decorator

    def init(self, dependencies: InitDependencies | None = None) -> Awaitable:
        """
        Call this method to init dependencies. Usually, it should be called
        when your application is starting up.

        This method works both for synchronous and asynchronous dependencies.
        If you call it without ``await``, it will initialize only sync dependencies.
        If you call it ``await init(...)``,
        it will initialize both sync and async dependencies.

        :param dependencies: dependencies to initialize. If this argument
            is passed - init dependencies specified in the registry will be ignored.
        """
        if dependencies is None:
            dependencies = self._for_init_list()
        elif callable(dependencies):
            dependencies = dependencies()

        sync_deps: list[DependencyCallable] = []
        async_deps: list[DependencyCallable] = []
        for dep in dependencies:
            provider = self._storage.get(dep)
            if not isinstance(provider.scope, ManualScope):
                raise ValueError(
                    f"Dependency {dep} is not in ManualScope, "
                    "you cannot initialize it manually."
                )
            if provider.is_async:
                async_deps.append(dep)
            else:
                sync_deps.append(dep)

        if sync_deps:
            call_cm_sync(self.resolve(*sync_deps))
        if async_deps:
            return call_cm_async(self.aresolve(*async_deps))
        return NullAwaitable()

    def _for_init_list(self) -> list[DependencyCallable]:
        dependencies: list[DependencyCallable] = []
        for item in self._for_init:
            if callable(item):
                item = item()
            dependencies.extend(item)
        return dependencies

    def shutdown(self, scope_class: LifespanScopeClass = ManualScope) -> Awaitable:
        """
        Call this method to close dependencies. Usually, it should be called
        when your application is shut down.

        This method works both for synchronous and asynchronous dependencies.
        If you call it without ``await``, it will shutdown only sync dependencies.
        If you call it ``await shutdown()``, it will shutdown both
        sync and async dependencies.

        If you not pass any arguments,
        it will shutdown subclasses of :class:`ManualScope`.

        :param scope_class: you can specify the scope class to shutdown. If passed -
            only dependencies of this scope class and its subclasses will be shutdown.
        """
        tasks = [
            instance.shutdown(global_key=self.shutdown)  # type: ignore[union-attr]
            for klass, instance in self._storage.scopes.items()
            if issubclass(klass, scope_class)
        ]
        tasks = [task for task in tasks if not isinstance(task, NullAwaitable)]
        return asyncio.gather(*tasks) if tasks else NullAwaitable()

    @contextmanager
    def lifespan(self) -> Generator[None]:
        """
        Context manager to manage the lifespan of the application.
        It will automatically call init and shutdown methods.
        """
        self.init()
        try:
            yield
        finally:
            self.shutdown()

    @asynccontextmanager
    async def alifespan(self) -> AsyncGenerator[None]:
        """
        Async context manager to manage the lifespan of the application.
        It will automatically call init and shutdown methods.
        """
        await self.init()
        try:
            yield
        finally:
            await self.shutdown()

    @property
    def touched(self) -> frozenset[DependencyCallable]:
        """
        Get all dependencies that were used during the picodi lifecycle.
        This method will return a frozenset of dependencies that were resolved.
        It will not include dependencies that were overridden.
        Primarily used for testing purposes.
        For example, you can check that mongo
        database was used in the test and clear it after the test.
        """
        return frozenset(self._storage.touched_dependencies)

    def override(
        self,
        dependency: DependencyCallable,
        new_dependency: DependencyCallable | None,
    ) -> ContextManager[None]:
        """
        Override a dependency with a new one. It can be used as a context manager
        or as a regular method call. New dependency will be
        added to the registry.

        :param dependency: dependency to override
        :param new_dependency: new dependency to use. If explicitly set to ``None``,
            it will remove the override.

        Examples
        --------
        .. code-block:: python

            with registry.override(get_settings, real_settings):
                pass

            registry.override(get_settings, real_settings)
            registry.override(get_settings, None)  # clear override
        """
        if self._storage.get_original(dependency):
            raise ValueError("Cannot override an overridden dependency")

        with lock:
            call_dependency = self._storage.overrides.get(dependency)
            if new_dependency is not None:
                self._storage.add(new_dependency)
                if dependency is new_dependency:
                    raise ValueError("Cannot override a dependency with itself")
                self._storage.overrides[dependency] = new_dependency
            else:
                self._storage.overrides.pop(dependency, None)

        @contextmanager
        def manage_context() -> Generator[None]:
            try:
                yield
            finally:
                self.override(dependency, call_dependency)

        return manage_context()

    def resolve(self, *dependency: DependencyCallable) -> ContextManager:
        """
        Resolve dependencies synchronously. Return a context manager that will
        return tuple of results of the dependencies in the order they were passed.
        If you pass only one dependency, it will return the result of that dependency.
        :param dependencies: dependencies to resolve.
        :return: sync context manager.
        """
        return self._storage.resolve(list(dependency), self, is_async=False)

    def aresolve(self, *dependency: DependencyCallable) -> AsyncContextManager:
        """
        Resolve dependencies asynchronously. Return a context manager that will
        return tuple of results of the dependencies in the order they were passed.
        If you pass only one dependency, it will return the result of that dependency.
        Also can resolve sync dependencies in async context.
        :param dependencies: dependencies to resolve.
        :return: async context manager.
        """
        return self._storage.resolve(list(dependency), self, is_async=True)

    def clear_overrides(self) -> None:
        """
        Clear all overrides. It will remove all overrides, but keep the dependencies.
        """
        self._storage.overrides.clear()

    def clear_touched(self) -> None:
        """
        Clear the touched dependencies.
        It will remove list of all dependencies resolved during the picodi lifecycle.
        """
        self._storage.touched_dependencies.clear()

    def _clear(self) -> None:
        """
        Clear the registry. It will remove all dependencies, overrides
        and touched dependencies.
        This method will not close any dependencies. So you need to manually call
        :func:`shutdown` before this method.
        It is useful for testing purposes, when you want to clear the registry
        and start from scratch.
        """
        self._storage.deps.clear()
        self._storage.overrides.clear()
        self._storage.touched_dependencies.clear()
        self._for_init.clear()


@dataclass(frozen=True)
class Provider:
    dependency: DependencyCallable
    is_async: bool
    scope: ScopeType

    @classmethod
    def from_dependency(
        cls,
        dependency: DependencyCallable,
        scope: ScopeType,
    ) -> Provider:
        return cls(
            dependency=dependency,
            is_async=is_async_function(dependency),
            scope=scope,
        )

    def get_scope(self) -> ScopeType:
        return self.scope

    def resolve_value(
        self,
        exit_stack: ExitStack | None,
        registry: Registry,
        dependant: Callable,
        kwargs: dict[str, Any],
    ) -> Any:
        signature = inspect.signature(self.dependency)
        registry_param = signature.parameters.get("registry")
        if registry_param and registry_param.default is signature.empty:
            kwargs["registry"] = registry

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
                        return await exit_stack.enter_context(context_manager())
                    return await scope.enter(context_manager(), global_key=dependant)
                elif isinstance(value_or_gen_, _AsyncGeneratorContextManager):
                    if isinstance(scope, AutoScope):
                        assert exit_stack is not None, "exit_stack is required"
                        return await exit_stack.enter_context(
                            _recreate_cm(value_or_gen_)
                        )
                    return await scope.enter(
                        _recreate_cm(value_or_gen_), global_key=dependant
                    )
                return value_or_gen_

            return resolve_value_inner()

        if inspect.isgenerator(value_or_gen):
            context_manager = contextmanager(lambda *args, **kwargs: value_or_gen)
            if isinstance(scope, AutoScope):
                assert exit_stack is not None, "exit_stack is required"
                return exit_stack.enter_context(context_manager())
            return scope.enter(context_manager(), global_key=dependant)
        elif isinstance(value_or_gen, _GeneratorContextManager):
            if isinstance(scope, AutoScope):
                assert exit_stack is not None, "exit_stack is required"
                return exit_stack.enter_context(_recreate_cm(value_or_gen))
            return scope.enter(_recreate_cm(value_or_gen), global_key=dependant)
        return value_or_gen


def _recreate_cm(
    gen: AsyncContextManager | ContextManager,
) -> AsyncContextManager | ContextManager:
    return gen._recreate_cm()  # type: ignore[union-attr]  # noqa: SF01


lock = threading.RLock()
registry = Registry()
registry.__doc__ = """
Picodi registry. You can use it to register dependencies, scopes, overrides,
initialize and shutdown dependencies.
"""
