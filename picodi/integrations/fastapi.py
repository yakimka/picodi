from __future__ import annotations

import inspect
from typing import Any

from picodi._picodi import DependencyCallable, Depends
from picodi.integrations.starlette import PicodiRequestScopeMiddleware, RequestScope

__all__ = [
    "Provide",
    "RequestScope",
    "PicodiRequestScopeMiddleware",
]


class DependsCallable(Depends):
    def __call__(self) -> Any:
        return self


class DependsAsyncCallable(Depends):
    async def __call__(self) -> Any:
        return self


def Provide(dependency: DependencyCallable, /) -> Any:  # noqa: N802
    if inspect.iscoroutinefunction(dependency):
        return DependsAsyncCallable(dependency)
    return DependsCallable(dependency)
