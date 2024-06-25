from __future__ import annotations

from typing import Any

from fastapi import Depends as FastAPIDepends

from picodi._picodi import DependencyCallable, Depends
from picodi.integrations.starlette import RequestScope, RequestScopeMiddleware

__all__ = [
    "Provide",
    "RequestScope",
    "RequestScopeMiddleware",
]


class DependsAsyncCallable(Depends):
    async def __call__(self) -> Any:
        return self


def Provide(  # noqa: N802
    dependency: DependencyCallable, /, *, wrap: bool = False
) -> Any:
    """
    Drop-in replacement for :func:`picodi.Provide` but for FastAPI.

    :param dependency: callable dependency.
    :param wrap: wrap dependency in ``fastapi.Depends``.
    """
    dep = DependsAsyncCallable(dependency)
    return FastAPIDepends(dep) if wrap else dep  # type: ignore[arg-type]
