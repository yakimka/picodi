.. _topics_lifespan:

.. testcleanup:: *

    import asyncio
    from picodi import registry


    async def teardown():
        await registry.shutdown()
        registry._clear()


    asyncio.run(teardown())


###################
Lifespan Management
###################

While scopes control the lifecycle of individual dependency instances during application runtime,
Picodi also provides mechanisms to manage the overall setup and teardown phases of your application, particularly for
dependencies with manual :ref:`scopes <topics_scopes>` like :class:`~picodi.SingletonScope` or :class:`~picodi.ContextVarScope`.

This involves two main operations:

1.  **Initialization:** Eagerly creating certain dependencies (especially singletons) when the application starts.
2.  **Shutdown:** Cleaning up resources held by manual-scoped dependencies when the application stops.

Picodi offers methods on the :attr:`~picodi.registry` object and convenient context managers to handle this.

***********************************
Initialization: ``registry.init()``
***********************************

The :meth:`picodi.Registry.init` method is used to initialize dependencies proactively.
This is often done once at application startup.

**Why Initialize?**

*   **Performance:** Avoid the cost of creating expensive dependencies (like database connection pools) on the first request.
*   **Readiness:** Ensure essential services are ready before the application starts serving requests or processing tasks.
*   **Async in Sync:** Pre-initialize async singletons so their values can be injected into sync functions later
    (see the :ref:`section <topics_async_in_sync>` on injecting async dependencies
    into sync functions in :doc:`/topics/async`)

**How it Works:**

``registry.init()`` initializes dependencies that have been registered for initialization in one of two ways:

1.  Using ``auto_init=True`` in :meth:`~picodi.Registry.set_scope`:

    .. testcode:: registry_init

        from picodi import registry, SingletonScope


        @registry.set_scope(SingletonScope, auto_init=True)
        def get_cache_client():
            print("Initializing Cache Client...")
            # ... create and return client ...
            return "RedisClient"

2.  Using :meth:`~picodi.Registry.add_for_init`:

    .. testcode:: registry_init

        from picodi import registry, SingletonScope


        @registry.set_scope(SingletonScope)  # No auto_init here
        def get_db_pool():
            print("Initializing DB Pool...")
            # ... create and return pool ...
            return "DbPool"


        # Explicitly add it to the init list
        registry.add_for_init([get_db_pool])  # Can pass a list or callable returning a list

**Calling init():**

You typically call ``registry.init()`` once during application startup.

.. testcode:: registry_init

    # At application startup
    print("App Starting...")
    registry.init()
    # If you have async dependencies marked for init, instead you MUST await
    # await registry.init()
    print("Dependencies Initialized.")

    # Application runs...

**Output:**

.. testoutput:: registry_init

    App Starting...
    Initializing Cache Client...
    Initializing DB Pool...
    Dependencies Initialized.

**Async Initialization:**

If any dependencies marked for initialization (via ``auto_init`` or ``add_for_init``) are ``async def`` or async generators,
``registry.init()`` returns an **awaitable**. You *must* ``await`` this awaitable in an async context to ensure
those dependencies are properly initialized. If all initializable dependencies are synchronous,
the awaitable does nothing when awaited.

.. testcode:: async_registry_init

    import asyncio
    from picodi import registry, SingletonScope


    @registry.set_scope(SingletonScope, auto_init=True)
    async def get_async_service_client():
        print("Initializing Async Client...")
        await asyncio.sleep(0.1)
        return "AsyncServiceClient"


    async def startup():
        print("App Starting...")
        # Must await because get_async_service_client is async
        await registry.init()
        print("Async Dependencies Initialized.")


    asyncio.run(startup())

**Output:**

.. testoutput:: async_registry_init

    App Starting...
    Initializing Async Client...
    Async Dependencies Initialized.

**Explicit Dependencies:**

You can also pass an explicit list (or callable returning a list) of dependencies to
``registry.init()`` if you want to initialize specific dependencies ad-hoc,
ignoring those registered via ``auto_init`` or ``add_for_init``.

.. code-block:: python

    registry.init([my_specific_dep_1, my_specific_dep_2])

*********************************
Shutdown: ``registry.shutdown()``
*********************************

The :meth:`picodi.Registry.shutdown` method is used to trigger the cleanup phase for dependencies managed
by **manual scopes** (``SingletonScope``, ``ContextVarScope``, or custom manual scopes).
This is typically called once when the application is stopping.

**How it Works:**

``registry.shutdown()`` iterates through the specified manual scopes (or all manual scopes if none are specified)
and calls their respective ``shutdown`` methods. For yield dependencies within these scopes,
this triggers the execution of the code after the ``yield`` statement (usually in the ``finally`` block).

.. testcode:: registry_shutdown

    from picodi import registry, SingletonScope, Provide, inject


    @registry.set_scope(SingletonScope)
    def get_resource_with_cleanup():
        print("Resource Acquired")
        try:
            yield "ResourceData"
        finally:
            print("Resource Cleaned Up")


    @inject
    def use_resource(res=Provide(get_resource_with_cleanup)):
        print(f"Using {res}")


    # --- Usage ---
    use_resource()  # Acquires resource if not already done

    print("App Shutting Down...")
    shutdown_awaitable = registry.shutdown()
    # Must await if any manual-scoped async dependencies need cleanup
    # await shutdown_awaitable
    print("Shutdown Complete.")

**Output:**

.. testoutput:: registry_shutdown

    Resource Acquired
    Using ResourceData
    App Shutting Down...
    Resource Cleaned Up
    Shutdown Complete.

**Specifying Scopes:**

By default, ``registry.shutdown()`` cleans up all manual scopes (``SingletonScope``, ``ContextVarScope``, etc.).
You can target specific scope classes using the ``scope_class`` argument:

.. code-block:: python

    # Only shutdown ContextVarScope dependencies (e.g., at the end of a request)
    await registry.shutdown(scope_class=ContextVarScope)

    # Shutdown SingletonScope dependencies (e.g., at app exit)
    await registry.shutdown(scope_class=SingletonScope)

**Async Shutdown:**

Similar to ``init()``, if any manual-scoped dependencies requiring cleanup are asynchronous (async generators),
``registry.shutdown()`` returns an **awaitable**.
You *must* ``await`` it in an async context to ensure proper asynchronous cleanup.

************************************************
Context Managers: ``lifespan`` and ``alifespan``
************************************************

Manually calling ``init()`` at the start and ``shutdown()`` at the end works, but Picodi provides
convenient context managers to handle this automatically, which is ideal for scripts, background workers,
or simple applications.

``registry.lifespan()`` (Synchronous)
=====================================
Use this for applications where the main lifecycle is synchronous.

.. testcode:: registry_lifespan

    from picodi import registry, SingletonScope, Provide, inject


    @registry.set_scope(SingletonScope, auto_init=True)
    def get_sync_singleton():
        print("Sync Singleton Init")
        yield "Sync Data"
        print("Sync Singleton Cleanup")


    @inject
    def main_sync_logic(data=Provide(get_sync_singleton)):
        print(f"Running sync logic with: {data}")


    print("Entering lifespan...")
    with registry.lifespan():  # Handles init() and shutdown()
        main_sync_logic()
    print("Exited lifespan.")

**Output:**

.. testoutput:: registry_lifespan

    Entering lifespan...
    Sync Singleton Init
    Running sync logic with: Sync Data
    Sync Singleton Cleanup
    Exited lifespan.

``registry.alifespan()`` (Asynchronous)
=======================================
Use this for applications with an asynchronous main lifecycle.
It handles ``await registry.init()`` and ``await registry.shutdown()``.

.. testcode:: registry_alifespan

    import asyncio
    from picodi import registry, SingletonScope, Provide, inject


    @registry.set_scope(SingletonScope, auto_init=True)
    async def get_async_singleton():
        print("Async Singleton Init")
        await asyncio.sleep(0.05)
        yield "Async Data"
        print("Async Singleton Cleanup")
        await asyncio.sleep(0.05)


    @inject
    async def main_async_logic(data=Provide(get_async_singleton)):
        print(f"Running async logic with: {data}")


    async def run_app():
        print("Entering alifespan...")
        async with registry.alifespan():  # Handles await init() and await shutdown()
            await main_async_logic()
        print("Exited alifespan.")


    asyncio.run(run_app())

**Output:**

.. testoutput:: registry_alifespan

    Entering alifespan...
    Async Singleton Init
    Running async logic with: Async Data
    Async Singleton Cleanup
    Exited alifespan.

These context managers significantly simplify managing the setup and teardown phases
for applications that don't have complex startup/shutdown sequences handled by a framework.

****************
Key Takeaways
****************

*   Use :meth:`~picodi.Registry.init` (often with ``auto_init=True`` or ``add_for_init``) at startup to
    eagerly initialize dependencies. ``await`` it if initializing async dependencies.
*   Use :meth:`~picodi.Registry.shutdown` at exit to clean up manual-scoped dependencies
    (:class:`~picodi.SingletonScope`, :class:`~picodi.ContextVarScope`). ``await`` it if cleaning up async dependencies.
*   Use ``with registry.lifespan():`` for simple synchronous application lifecycles.
*   Use ``async with registry.alifespan():`` for simple asynchronous application lifecycles.
*   Proper lifespan management ensures resources are initialized correctly and released cleanly.

Next, let's focus specifically on considerations when working with :ref:`Asynchronous Code <topics_async>`.
