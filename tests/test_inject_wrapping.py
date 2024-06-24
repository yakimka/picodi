import inspect

from picodi import Provide, inject


def get_value(): ...


def test_inject_doesnt_change_type_of_function():
    @inject
    def my_dependency(value: int = Provide(get_value)): ...

    assert inspect.isfunction(my_dependency)
    assert not inspect.iscoroutinefunction(my_dependency)
    assert not inspect.isgeneratorfunction(my_dependency)
    assert not inspect.isasyncgenfunction(my_dependency)


def test_inject_doesnt_change_type_of_async_function():
    @inject
    async def my_dependency(value: int = Provide(get_value)): ...

    assert inspect.iscoroutinefunction(my_dependency)


def test_inject_doesnt_change_type_of_generator():
    @inject
    def my_dependency(value: int = Provide(get_value)):
        yield value  # pragma: no cover

    assert inspect.isgeneratorfunction(my_dependency)


def test_inject_doesnt_change_type_of_async_generator():
    @inject
    async def my_dependency(value: int = Provide(get_value)):
        yield value  # pragma: no cover

    assert inspect.isasyncgenfunction(my_dependency)
