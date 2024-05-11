from typing import Any

sentinel = object()


class PathNotFoundError(Exception):
    def __init__(self, current_path: str, obj: Any):
        self.current_path = current_path
        self.obj = obj
        super().__init__(f"Can't find path '{current_path}' in {type(obj)} object")


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
