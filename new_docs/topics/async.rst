.. _topics_async:

##################
Asynchronous Code
##################

Picodi provides first-class support for Python's ``asyncio`` and asynchronous programming patterns. You can define, inject, and manage the lifecycle of asynchronous dependencies just as easily as synchronous ones.

********************************
Defining Async Dependencies
********************************

To define a dependency provider that performs asynchronous operations, simply use ``async def``:

.. code-block:: python

    import asyncio


    async def fetch_remote_config() -> dict:
        """Simulates fetching configuration over the network."""
        print("Async Dep: Fetching config...")
        await asyncio.sleep(0.1)  # Simulate network I/O
        return {"feature_x_enabled": True}

This function can now be used with :func:`~picodi.Provide`.

********************************
Async Yield Dependencies
********************************

For asynchronous resources that require setup and teardown (like database connections or client sessions), use an ``async def`` function with a single ``yield``. This works like :func:`python:contextlib.asynccontextmanager`.

.. code-block:: python

    import asyncio
    from contextlib import asynccontextmanager


    class AsyncDbClient:
        async def connect(self):
            print("Async Yield Dep: Connecting...")
            await asyncio.sleep(0.05)
            return self

        async def close(self):
            print("Async Yield Dep: Closing connection...")
            await asyncio.sleep(0.05)

        async def query(self, sql):
            print(f"Async Yield Dep: Running query: {sql}")
            await asyncio.sleep(0.1)
            return [{"id": 1}, {"id": 2}]


    @asynccontextmanager
    async def get_db_client():
        client = AsyncDbClient()
        await client.connect()
        try:
            yield client  # Yield the connected client
        finally:
            await client.close()

Picodi will handle awaiting the setup phase (before ``yield``) and the teardown phase (after ``yield``).

********************************
Injecting Async Dependencies
********************************

Rule of Thumb: **If a function needs to inject an asynchronous dependency, the function itself must be ``async def``.**

This is because Picodi needs to ``await`` the asynchronous dependency provider during the injection process.

.. code-block:: python

    from picodi import Provide, inject

    # Assume async dependencies from above are defined


    @inject
    async def process_data(
        config: dict = Provide(fetch_remote_config),
        db_client=Provide(get_db_client),  # Injecting async yield dep
    ):
        print(f"Async Service: Got config: {config}")
        if config.get("feature_x_enabled"):
            results = await db_client.query("SELECT * FROM data")
            print(f"Async Service: Got DB results: {results}")


    # To run this:
    # import asyncio
    # asyncio.run(process_data())

An ``async def`` function can, however, inject regular **synchronous** dependencies without any issues. Picodi handles mixing them correctly.

.. code-block:: python

    def get_sync_setting() -> str:
        return "sync_value"


    @inject
    async def async_func_with_sync_dep(
        sync_val: str = Provide(get_sync_setting),
        async_val: dict = Provide(fetch_remote_config),
    ):
        print(f"Received sync: {sync_val}, async: {async_val}")

*******************************************
Lifespan Management (``init``/``shutdown``)
*******************************************

When dealing with async dependencies that have :ref:`manual scopes <topics_scopes>` (``SingletonScope``, ``ContextVarScope``) or are marked for eager initialization (``auto_init=True``), remember:

*   :meth:`picodi.Registry.init` returns an **awaitable**. If any async dependencies are being initialized, you **must** ``await registry.init()``.
*   :meth:`picodi.Registry.shutdown` returns an **awaitable**. If any async dependencies require cleanup (e.g., async yield dependencies in manual scopes), you **must** ``await registry.shutdown()``.

The :meth:`~picodi.Registry.alifespan` context manager handles these awaits automatically for applications with an async lifecycle.

.. code-block:: python
    :emphasize-lines: 10, 16

    import asyncio
    from picodi import registry, SingletonScope, Provide, inject


    @registry.set_scope(SingletonScope, auto_init=True)
    async def get_async_singleton_resource():
        print("Async Singleton: Init")
        yield "Async Resource Data"
        print("Async Singleton: Cleanup")


    @inject
    async def main_logic(res=Provide(get_async_singleton_resource)):
        print(f"Main logic using: {res}")


    async def run():
        async with registry.alifespan():  # Handles await init() and await shutdown()
            await main_logic()


    # asyncio.run(run())

*************************************************
Injecting Async Dependencies into Sync Functions
*************************************************
.. _topics_async_in_sync:

Generally, you cannot directly inject the *result* of an async dependency into a synchronous function, because the sync function cannot ``await`` the dependency resolution. Trying to do so will inject the coroutine object itself.

**However, there's a common pattern for async dependencies with manual scopes (like ``SingletonScope``):**

1.  Define the async dependency with a manual scope (e.g., ``SingletonScope``).
2.  Ensure the dependency is initialized **before** the synchronous function needs it. This is typically done by calling ``await registry.init()`` at application startup (using ``auto_init=True`` or ``add_for_init``).
3.  Once initialized, the *cached value* of the async dependency exists in the scope.
4.  A synchronous function can now inject this dependency. Picodi will retrieve the already-computed value from the scope cache without needing to ``await`` the provider function again.

.. code-block:: python

    import asyncio
    from picodi import registry, SingletonScope, Provide, inject


    @registry.set_scope(SingletonScope, auto_init=True)  # Manual scope, eager init
    async def get_async_data_source():
        print("Async Source: Initializing...")
        await asyncio.sleep(0.1)
        return {"data": "pre-loaded async data"}


    @inject  # Synchronous function
    def process_synchronously(
        source: dict = Provide(get_async_data_source),  # Provide the async dep
    ):
        # This works because the value was already created and cached by init()
        print(f"Sync function using cached async data: {source}")


    async def startup_and_run():
        print("App Startup: Initializing dependencies...")
        await registry.init()  # MUST await to initialize get_async_data_source
        print("App Startup: Dependencies initialized.")

        print("\nRunning synchronous function...")
        process_synchronously()

        print("\nApp Shutdown...")
        await registry.shutdown()  # Cleanup (if get_async_data_source yielded)


    # asyncio.run(startup_and_run())

**Output (if run):**

.. code-block:: text

    App Startup: Initializing dependencies...
    Async Source: Initializing...
    App Startup: Dependencies initialized.

    Running synchronous function...
    Sync function using cached async data: {'data': 'pre-loaded async data'}

    App Shutdown...
    App Shutdown Complete.

This pattern is very useful for sharing resources like database connection pools or HTTP clients (initialized asynchronously) with both async and sync parts of your application.

****************
Key Takeaways
****************

*   Use ``async def`` for asynchronous dependency providers.
*   Use ``async def`` with ``yield`` for async dependencies requiring setup/teardown.
*   Functions injecting async dependencies must be ``async def``.
*   Async functions can inject sync dependencies.
*   ``await registry.init()`` and ``await registry.shutdown()`` if dealing with async dependencies in manual scopes or marked for ``auto_init``.
*   Pre-initialize async dependencies with manual scopes using ``await registry.init()`` to allow injection into synchronous functions.

Next, let's focus on how Picodi helps with :ref:`Testing <topics_testing>`.
