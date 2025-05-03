from __future__ import annotations

import inspect
import threading
from collections.abc import Callable, Generator
from contextlib import asynccontextmanager, contextmanager
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, ContextManager, overload

from picodi._scopes import (
    AutoScope,
    ContextVarScope,
    NullScope,
    ScopeType,
    SingletonScope,
)

if TYPE_CHECKING:
    from picodi.support import ExitStack

DependencyCallable = Callable[..., Any]
unset = object()


class Storage:
    def __init__(self) -> None:
        self.deps: dict[DependencyCallable, Provider] = {}
        self.overrides: dict[DependencyCallable, DependencyCallable] = {}
        self.touched_dependencies: set[DependencyCallable] = set()
        self.scopes: dict[type[ScopeType], ScopeType] = {
            NullScope: NullScope(),
            SingletonScope: SingletonScope(),
            ContextVarScope: ContextVarScope(),
        }

    def add(
        self,
        dependency: DependencyCallable,
        scope_class: type[ScopeType] = NullScope,
    ) -> None:
        """
        Add a dependency to the registry.
        """
        with lock:
            if dependency not in self.deps:
                self.deps[dependency] = Provider.from_dependency(
                    dependency=dependency,
                    scope_class=scope_class,
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

    def __init__(self, storage: Storage) -> None:
        self._storage = storage

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

    @overload
    def override(
        self, dependency: DependencyCallable, new_dependency: None = None
    ) -> Callable[[DependencyCallable], DependencyCallable]:
        pass

    @overload
    def override(
        self, dependency: DependencyCallable, new_dependency: DependencyCallable
    ) -> ContextManager[None]:
        pass

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
                pass

            registry.override(get_settings, real_settings)
            registry.override(get_settings, None)  # clear override
        """
        if self._storage.get_original(dependency):
            raise ValueError("Cannot override an overridden dependency")

        def decorator(override_to: DependencyCallable) -> DependencyCallable:
            self._storage.add(override_to)
            if dependency is override_to:
                raise ValueError("Cannot override a dependency with itself")
            self._storage.overrides[dependency] = override_to
            return override_to

        if new_dependency is unset:
            return decorator

        with lock:
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
        self._storage.overrides.clear()

    def clear_touched(self) -> None:
        """
        Clear the touched dependencies.
        It will remove all dependencies resolved during the picodi lifecycle.
        """
        self._storage.touched_dependencies.clear()

    def clear(self) -> None:
        """
        Clear the registry. It will remove all dependencies and overrides.
        This method will not close any dependencies. So you need to manually call
        :func:`shutdown_dependencies` before this method.
        """
        self._storage.deps.clear()
        self._storage.overrides.clear()
        self._storage.touched_dependencies.clear()


@dataclass(frozen=True)
class Provider:
    dependency: DependencyCallable
    is_async: bool
    scope_class: type[ScopeType]

    @classmethod
    def from_dependency(
        cls,
        dependency: DependencyCallable,
        scope_class: type[ScopeType],
    ) -> Provider:
        is_async = inspect.iscoroutinefunction(
            dependency
        ) or inspect.isasyncgenfunction(dependency)
        return cls(
            dependency=dependency,
            is_async=is_async,
            scope_class=scope_class,
        )

    def get_scope(self) -> ScopeType:
        return storage.scopes[self.scope_class]

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


lock = threading.RLock()
storage = Storage()
registry = Registry(storage)
