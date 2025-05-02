from __future__ import annotations

from typing import Any

from fastapi import Depends as FastAPIDepends

from picodi._types import DependencyCallable, Depends
from picodi.helpers import resolve
from picodi.integrations.starlette import RequestScope, RequestScopeMiddleware

__all__ = [
    "Provide",
    "RequestScope",
    "RequestScopeMiddleware",
]


class DependsAsyncCallable(Depends):
    async def __call__(self) -> Any:
        return self


class DependsAsyncStandaloneCallable(Depends):
    async def __call__(self) -> Any:
        async with resolve(self.call) as result:
            yield result


def Provide(  # noqa: N802
    dependency: DependencyCallable, /, *, wrap: bool = False
) -> Any:
    """
    Drop-in replacement for :func:`picodi.Provide` but for FastAPI.

    :param dependency: callable dependency.
    :param wrap: wrap dependency in ``fastapi.Depends``. In this mode you can use
        ``picodi`` dependencies in FastAPI routes
        without :func:`picodi.inject` decorator.
    """
    if wrap:
        return FastAPIDepends(
            DependsAsyncStandaloneCallable(dependency),  # type: ignore[arg-type]
        )

    return DependsAsyncCallable(dependency)
