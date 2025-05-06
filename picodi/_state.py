from __future__ import annotations

import asyncio
import inspect
import threading
from collections.abc import AsyncGenerator, Awaitable, Callable, Generator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, AsyncContextManager, ContextManager, TypeVar

from picodi._internal import LazyResolver
from picodi._scopes import AutoScope, ManualScope, NullScope, ScopeType
from picodi.support import ExitStack, NullAwaitable, is_async_function

if TYPE_CHECKING:
    from picodi._types import DependencyCallable, InitDependencies, LifespanScopeClass


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

        async_deps: list[Awaitable] = []
        for dep in dependencies:
            provider = self._storage.get(dep)
            resolver = LazyResolver(provider)
            value = resolver(provider.is_async)
            if provider.is_async:
                async_deps.append(value)

        if async_deps:
            # asyncio.gather runs coros in different tasks with different context
            #   we can run them in current context with contextvars.copy_context()
            #   but in this case `ContextVarScope`
            #   will save values in the wrong context.
            #   So we fix it in dirty way by running all coros one by one until
            #   come up with better solution.
            async def init_all() -> None:
                for dep in async_deps:
                    await dep

            return init_all()
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
            instance.shutdown()  # type: ignore[call-arg]
            for klass, instance in self._storage.scopes.items()
            if issubclass(klass, scope_class)
        ]
        if all(isinstance(task, NullAwaitable) for task in tasks):
            return NullAwaitable()
        return asyncio.gather(*tasks)

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
                elif isinstance(value_or_gen_, AsyncContextManager):
                    if isinstance(scope, AutoScope):
                        assert exit_stack is not None, "exit_stack is required"
                        return await scope.enter(
                            exit_stack, _recreate_cm(value_or_gen_)
                        )
                    return await scope.enter(_recreate_cm(value_or_gen_))
                return value_or_gen_

            return resolve_value_inner()

        if inspect.isgenerator(value_or_gen):
            context_manager = contextmanager(lambda *args, **kwargs: value_or_gen)
            if isinstance(scope, AutoScope):
                assert exit_stack is not None, "exit_stack is required"
                return scope.enter(exit_stack, context_manager())
            return scope.enter(context_manager())
        elif isinstance(value_or_gen, ContextManager):
            if isinstance(scope, AutoScope):
                assert exit_stack is not None, "exit_stack is required"
                return scope.enter(exit_stack, _recreate_cm(value_or_gen))
            return scope.enter(_recreate_cm(value_or_gen))
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
