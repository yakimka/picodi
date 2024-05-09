from types import SimpleNamespace

import pytest

from picodi.helpers import get_value

SN = SimpleNamespace


@pytest.mark.parametrize("path,obj,expected", [
    ("foo", SN(foo=42), 42),
    ("foo.bar", SN(foo=SN(bar=101)), 101),
    ("foo.bar.baz", SN(foo=SN(bar=SN(baz=12))), 12),
    #
    # ("foo", dict(foo=42), 42),
    # ("foo.bar", dict(foo=dict(bar=101)), 101),
    # ("foo.bar.baz", dict(foo=dict(bar=dict(baz=12))), 12),
])
def test_get_simple_value(path, obj, expected):
    result = get_value(path, obj)

    assert result == expected


@pytest.mark.parametrize("path,obj", [
    ("oops", SN(foo=42)),
    ("foo.bar", SN(foo=42)),
    ("foo.bar.baz", SN(foo=SN(bar=101))),
])
def test_not_existing_path_raises_attribute_error(path, obj):
    with pytest.raises(AttributeError):
        get_value(path, obj)


@pytest.mark.parametrize("obj", [
    SN(foo=777),
])
def test_get_default_value_if_not_found(obj):
    result = get_value("foo.bar.baz2", obj, default="my_default_value")

    assert result == "my_default_value"
