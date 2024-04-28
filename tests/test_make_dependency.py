from typing import Any

import pytest

from picodi import Provide, inject, make_dependency


class MyClass:
    @inject
    def __init__(self, a: Any, b: Any):
        self.a = a
        self.b = b

    def __repr__(self):
        return f"MyClass({self.a}, {self.b})"

    def __eq__(self, other):
        return self.a == other.a and self.b == other.b


def create_my_class(a: Any, b: Any) -> MyClass:
    return MyClass(a, b)


@pytest.fixture(params=[create_my_class, MyClass])
def my_callable(request):
    return request.param


@pytest.mark.parametrize(
    "args,kwargs",
    [
        ((1, 2), {}),
        ((), {"a": 1, "b": 2}),
        ((1,), {"b": 2}),
    ],
)
def test_can_set_arguments_for_non_zero_arguments_function(args, kwargs, my_callable):
    partial_func = make_dependency(my_callable, *args, **kwargs)

    result = partial_func()

    assert result == MyClass(1, 2)


def test_cant_set_arguments_partially(my_callable):
    with pytest.raises(TypeError, match="missing"):
        make_dependency(my_callable, 1)


def test_can_override_arguments(my_callable):
    if my_callable is MyClass:
        pytest.skip("Can't override arguments for class")

    partial_func = make_dependency(my_callable, 1, b=2)

    result = partial_func(0, b=4)

    assert result == MyClass(0, 4)


def test_can_override_with_provider_and_it_will_be_resolved_on_call(my_callable):
    def get_ten() -> int:
        return 10

    partial_func = make_dependency(my_callable, 42, Provide(get_ten))

    result = partial_func()

    assert result == MyClass(42, 10)
