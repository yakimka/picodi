import operator
from types import SimpleNamespace
from typing import Any


sentinel = object()


def get_value(
    path: str, obj: Any, *, default: Any = sentinel
) -> Any:
    """
    Get attribute from nested objects.
    If the attribute is not found, raise an AttributeError if default is not provided.
    If default is provided, return it.

    Example:
    ```
    obj = SimpleNamespace(foo=SimpleNamespace(bar=SimpleNamespace(baz=42)))
    get_attribute("foo.bar.baz", obj)  # 42
    get_attribute("foo.bar.baz2", obj)  # AttributeError
    get_attribute("foo.bar.baz2", obj, default=12)  # 12
    ```
    """
    if not path:
        raise ValueError("Empty path")

    try:
        result = operator.attrgetter(path)(obj)
    except AttributeError:
        if default is sentinel:
            raise
        return default
    return result
