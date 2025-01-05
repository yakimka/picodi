Known Issues
============

Receiving a coroutine object instead of the actual value
--------------------------------------------------------

If you are trying to resolve async dependencies in sync functions, you will receive a coroutine object.
For regular dependencies, this is intended behavior, so only use async dependencies in async functions.
However, if your dependency (e.g. ``my_dependency``) uses a :class:`picodi.SingletonScope` scope,
you can call :func:`picodi.init_dependencies([my_dependency])` on app startup to resolve dependencies,
and then Picodi will use cached values, even in sync functions.

flake8-bugbear throws "B008 Do not perform function calls in argument defaults"
-------------------------------------------------------------------------------

Edit ``extend-immutable-calls`` in your ``setup.cfg``:

.. code-block:: ini

    [flake8]
    extend-immutable-calls = picodi.Provide,Provide

RuntimeError: Event loop is closed when using pytest-asyncio
------------------------------------------------------------

This error occurs because ``pytest-asyncio`` closes the event loop after the test finishes
and you are using :class:`picodi.ManualScope` scoped dependencies.

To fix this, you need to close all resources after the test finishes.
Add ``await shutdown_dependencies()`` at the end of your tests.

.. testcode::

    import picodi
    import pytest


    @pytest.fixture(autouse=True)
    async def _setup_picodi():
        yield
        await picodi.shutdown_dependencies()


Or use integration with ``pytest-asyncio``, more details in :doc:`testing` section.
