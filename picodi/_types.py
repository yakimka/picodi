from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any, NamedTuple

from picodi._scopes import ManualScope

DependencyCallable = Callable[..., Any]
InitDependencies = (
    Iterable[DependencyCallable] | Callable[[], Iterable[DependencyCallable]]
)
LifespanScopeClass = type[ManualScope] | tuple[type[ManualScope], ...]


class Depends(NamedTuple):
    call: DependencyCallable


@dataclass
class DependNode:
    value: DependencyCallable
    name: str | None
    dependencies: list[DependNode]
