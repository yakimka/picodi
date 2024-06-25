from __future__ import annotations

from typing import Any

from picodi._picodi import DependencyCallable, Depends
from picodi.integrations.starlette import PicodiRequestScopeMiddleware, RequestScope

__all__ = [
    "Provide",
    "RequestScope",
    "PicodiRequestScopeMiddleware",
]


class DependsAsyncCallable(Depends):
    async def __call__(self) -> Any:
        return self


def Provide(dependency: DependencyCallable, /) -> Any:  # noqa: N802
    return DependsAsyncCallable(dependency)
