from types import SimpleNamespace

import pytest

from picodi.helpers import PathNotFoundError, get_value

SN = SimpleNamespace


@pytest.mark.parametrize(
    "path,obj,expected",
    [
        ("foo", SN(foo=42), 42),
        ("foo.bar", SN(foo=SN(bar=101)), 101),
        ("foo.bar.baz", SN(foo=SN(bar=SN(baz=12))), 12),
        #
        ("foo", {"foo": 42}, 42),
        ("foo.bar", {"foo": {"bar": 101}}, 101),
        ("foo.bar.baz", {"foo": {"bar": {"baz": 12}}}, 12),
        #
        ("foo.bar", SN(foo={"bar": 101}), 101),
        ("foo.bar", {"foo": SN(bar=101)}, 101),
        ("foo.bar.baz", SN(foo={"bar": SN(baz=12)}), 12),
        ("foo.bar.baz", {"foo": SN(bar={"baz": 12})}, 12),
    ],
)
def test_get_simple_value(path, obj, expected):
    result = get_value(path, obj)

    assert result == expected


@pytest.mark.parametrize(
    "path,obj",
    [
        ("oops", SN(foo=42)),
        ("foo.bar", SN(foo=42)),
        ("foo.bar.baz", SN(foo=SN(bar=101))),
    ],
)
def test_not_existing_path_raises_error(path, obj):
    with pytest.raises(PathNotFoundError):
        get_value(path, obj)


@pytest.mark.parametrize(
    "path,obj,expected_path",
    [
        ("oops", SN(foo=42), "oops"),
        ("foo.bar", SN(foo=42), "foo.bar"),
        ("foo.bar.baz", SN(foo=SN(bar=101)), "foo.bar.baz"),
        ("foo.ban", SN(foo=SN(bar=101)), "foo.ban"),
    ],
)
def test_not_existing_path_raises_error_with_proper_message(path, obj, expected_path):
    with pytest.raises(PathNotFoundError, match=f"Can't find path '{expected_path}'"):
        get_value(path, obj)


@pytest.mark.parametrize(
    "obj",
    [
        SN(foo=777),
    ],
)
def test_get_default_value_if_not_found(obj):
    result = get_value("foo.bar.baz2", obj, default="my_default_value")

    assert result == "my_default_value"


def test_cant_pass_empty_path():
    with pytest.raises(ValueError, match="Empty path"):
        get_value("", SN(foo=42))


def test_path_must_be_string():
    with pytest.raises(TypeError, match="Path must be a string"):
        get_value(42, SN(foo=42))
