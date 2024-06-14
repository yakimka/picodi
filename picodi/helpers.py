from __future__ import annotations

import asyncio
import contextlib
from typing import TYPE_CHECKING, Any, ParamSpec, TypeVar, overload

import picodi

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator, Callable, Generator
    from types import TracebackType

sentinel = object()


class PathNotFoundError(Exception):
    def __init__(self, current_path: str, obj: Any):
        self.current_path = current_path
        self.obj = obj
        super().__init__(f"Can't find path '{current_path}' in {type(obj)} object")


def get_value(path: str, obj: Any, *, default: Any = sentinel) -> Any:
    """
    Get attribute from nested objects.
    If the attribute is not found, raise an AttributeError if default is not provided.
    If default is provided, return it.

    Example:
    ```
    obj = SimpleNamespace(foo=SimpleNamespace(bar={"baz": 42}))
    get_value("foo.bar.baz", obj)  # 42
    get_value("foo.bar.baz2", obj)  # AttributeError
    get_value("foo.bar.baz2", obj, default=12)  # 12
    ```
    """
    if not path:
        raise ValueError("Empty path")
    if not isinstance(path, str):
        raise TypeError("Path must be a string")

    value = obj
    current_path = []
    for part in path.split("."):
        current_path.append(part)
        curr_val = _get_attr(value, part)
        if curr_val is sentinel:
            curr_val = _get_item(value, part)
        if curr_val is sentinel:
            if default is sentinel:
                raise PathNotFoundError(".".join(current_path), obj)
            return default
        value = curr_val

    return value


def _get_attr(obj: Any, attr: str) -> Any:
    try:
        return getattr(obj, attr)
    except AttributeError:
        return sentinel


def _get_item(obj: Any, key: str) -> Any:
    try:
        return obj[key]
    except (KeyError, TypeError):
        return sentinel


T = TypeVar("T")
P = ParamSpec("P")


class _Lifespan:
    @overload
    def __call__(self, fn: Callable[P, T]) -> Callable[P, T]:
        pass

    @overload
    def __call__(self, fn: None = None) -> Callable[[Callable[P, T]], Callable[P, T]]:
        pass

    def __call__(
        self, fn: Callable[P, T] | None = None
    ) -> Callable[P, T] | Callable[[Callable[P, T]], Callable[P, T]]:
        if fn is None:
            return self
        if asyncio.iscoroutinefunction(fn):
            return self.async_()(fn)  # type: ignore[return-value]
        return self.sync()(fn)

    def __enter__(self) -> None:
        picodi.init_dependencies()

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        picodi.shutdown_dependencies()

    async def __aenter__(self) -> None:
        await picodi.init_dependencies()

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await picodi.shutdown_dependencies()

    @contextlib.contextmanager
    def sync(self) -> Generator[None, None, None]:
        picodi.init_dependencies()
        try:
            yield
        finally:
            picodi.shutdown_dependencies()

    @contextlib.asynccontextmanager
    async def async_(self) -> AsyncGenerator[None, None]:
        await picodi.init_dependencies()
        try:
            yield
        finally:
            await picodi.shutdown_dependencies()  # noqa: ASYNC102


lifespan = _Lifespan()
