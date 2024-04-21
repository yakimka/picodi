import functools
import inspect
from collections.abc import Callable, Coroutine
from dataclasses import dataclass
from typing import Any, ParamSpec, TypeAlias, TypeVar

Dependency: TypeAlias = Callable[[], Any]

_not_injected = object()
_registry: dict[Dependency, Any] = {}
_shutdown_callbacks: list[Callable[[], None]] = []


def Depends(dependency: Dependency, /, use_cache: bool = True) -> Any:  # noqa: N802
    _registry[dependency] = _not_injected
    return _Depends(dependency, use_cache)


@dataclass
class _Depends:
    dependency: Dependency
    use_cache: bool


T = TypeVar("T")
P = ParamSpec("P")


def inject(fn: Callable[P, T]) -> Callable[P, T | Coroutine[Any, Any, T]]:
    signature = inspect.signature(fn)

    @functools.wraps(fn)
    def wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
        bound = signature.bind(*args, **kwargs)
        bound.apply_defaults()

        to_close = []
        for name, value in bound.arguments.items():
            if isinstance(value, _Depends):
                if not value.use_cache:
                    result, close_callback = _resolve_dependency(value.dependency)
                    bound.arguments[name] = result
                    if close_callback is not None:
                        to_close.append(close_callback)
                else:
                    if _registry.get(value.dependency) is _not_injected:
                        result, close_callback = _resolve_dependency(value.dependency)
                        _registry[value.dependency] = result
                        if close_callback is not None:
                            _shutdown_callbacks.append(close_callback)
                    bound.arguments[name] = _registry[value.dependency]

        result = fn(*bound.args, **bound.kwargs)
        for close_callback in to_close:
            close_callback()
        return result

    return wrapper


def shutdown_resources():
    for close_callback in _shutdown_callbacks:
        close_callback()


def _resolve_dependency(
    dependency: Dependency,
) -> tuple[Any, Callable[[], None] | None]:
    result = dependency()
    close_callback = None
    if inspect.isgeneratorfunction(dependency):
        generator = result
        result = next(generator)

        def close_callback():
            try:
                next(generator)
            except StopIteration:
                pass

    return result, close_callback
