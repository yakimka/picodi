Quick Start
===========

Instalation
-----------

First, you need to install the Picodi package.
You can do this by running the following command:

.. code-block:: bash

    pip install picodi

Dependencies
------------

Dependency in terms of Picodi is an any function without required arguments.
So this simple function is a Picodi dependency:

.. code-block:: python

    def simple_function() -> int:
        return 42

You can inject this dependency into your function or class by using
the :func:`picodi.inject` decorator and the :func:`picodi.Provide` marker.

.. code-block:: python

    from picodi import Provide, inject


    @inject
    def my_function(meaning_of_life: int = Provide(simple_function)) -> int:
        return meaning_of_life


    class MyClass:
        @inject
        def __init__(self, meaning_of_life: int = Provide(simple_function)) -> None:
            self.meaning_of_life = meaning_of_life


    assert my_function() == 42
    assert MyClass().meaning_of_life == 42

``my_function`` and ``MyClass`` will be injected with the ``simple_function`` dependency.

You can tell that the ``my_function`` is a function without required arguments so
it can also be a dependency. And you are right! You can inject ``my_function`` into
another function or class.

.. code-block:: python

    from picodi import Provide, inject


    @inject
    def another_function(meaning_of_life: int = Provide(my_function)) -> int:
        return meaning_of_life


    assert another_function() == 42

So if dependency is just a function, you can use closures to parametrize dependencies
or use them as a factory.

.. code-block:: python

    from picodi import Provide, inject


    def get_number(number: int):
        def number_factory() -> int:
            return number
        return number_factory


    @inject
    def my_function(value: int = Provide(get_number(42))) -> int:
        return value


    assert my_function() == 42

Yield Dependencies
------------------

Returning a values from dependencies is not enough. Sometimes you need not only to
initialize dependency but also to clean it up. For this purpose, you can use
functions that yield value.

.. code-block:: python

    from picodi import Provide, inject


    def get_file_for_read():
        file = open("file.txt")
        try:
            yield file
        finally:
            file.close()
            print("File closed")


    @inject
    def read_file(file=Provide(get_file_for_read)) -> str:
        return file.read()


    with open("file.txt", "w") as file:
        file.write("Hello, World!")


    assert read_file() == "Hello, World!"
    # Output: File closed

Manually calling ``close`` method on the file object is not necessary in this case,
you can use context manager to handle it.

.. code-block:: python

    from picodi import Provide, inject


    def get_file_for_read():
        with open("file.txt") as file:
            yield file
            print("File closed")

    # The rest of the code is the same as in the previous example

Any yield functions that are valid candidates for :func:`python:contextlib.contextmanager`
or :func:`python:contextlib.asynccontextmanager` can be used as yield dependencies.

Async Dependencies
------------------

All previous examples are synchronous. If you need to use asynchronous dependencies,
you can use async functions.

Some examples of async dependencies:

.. code-block:: python

    import asyncio

    from picodi import Provide, inject


    async def simple_async_dependency() -> int:
        return 42


    async def yield_async_dependency():
        yield 42
        print("Async dependency closed")


    @inject
    async def async_function(
        simple: int = Provide(simple_async_dependency),
        yield_: int = Provide(yield_async_dependency),
    ) -> int:
        return simple + yield_


    assert asyncio.run(async_function()) == 84
