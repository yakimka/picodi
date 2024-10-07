Known Issues
============

Receiving a coroutine object instead of the actual value
--------------------------------------------------------

If you are trying to resolve async dependencies in sync functions, you will receive a coroutine object.
For regular dependencies, this is intended behavior, so only use async dependencies in async functions.
However, if your dependency uses a scope inherited from :class:`picodi.ManualScope`,
and used ``use_init_hook=True`` with :func:`dependency` decorator,
you can use :func:`picodi.init_dependencies` on app startup to resolve dependencies,
and then Picodi will use cached values, even in sync functions.

Dependency not initialized with init_dependencies()
-----------------------------------------------------

1. Ensure that your dependency defined with scopes inherited from :class:`picodi.ManualScope`.
2. Ensure that your dependency is decorated with parameter ``use_init_hook=True`` of :func:`dependency` decorator
3. If you have async dependency, ensure that you are calling ``await init_dependencies()`` in an async context.
4. Ensure that modules with your dependencies are imported (e.g., registered) before calling :func:`picodi.init_dependencies()`.

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
