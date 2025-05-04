Scopes
======

While resolving dependency values and injecting them is a good starting point,
it's insufficient on its own.
We also need control over the lifecycle of the objects we create.
This is where scopes come in.

Picodi has two types of scopes: auto and manual. The lifecycle of auto-scopes is managed
by Picodi itself. Auto-scopes are initialized and closed automatically.
Manual scopes are initialized on the first injection or when :func:`picodi.registry.init`
is explicitly called by the user and closed when :func:`picodi.registry.shutdown` is called.

Use the :func:`picodi.registry.set_scope` decorator with the ``scope_class`` argument
to set a dependency's scope. Example:

.. code-block:: python

    from picodi import SingletonScope, registry


    @registry.set_scope(SingletonScope)
    def get_singleton():
        return object()

Built-in scopes
---------------

NullScope
*********

By default, dependencies use the :class:`picodi.NullScope` scope creating
a new instance every time they are injected.
This means that a new instance is created every time the dependency is injected
and closed immediately after root injection is done.

SingletonScope
**************

The :class:`picodi.SingletonScope` creates a single instance of the dependency.
This instance is reused every time the dependency is injected.

``SingletonScope`` is a manual scope, so you need to call :func:`picodi.registry.shutdown`
manually. Usually you want to call it when your application is shutting down.

ContextVarScope
***************

The :class:`picodi.ContextVarScope` relies on :class:`python:contextvars.ContextVar`
to store instances.

``ContextVarScope`` is the manual scope, so you need to call :func:`picodi.registry.shutdown`
with ``scope_class=ContextVarScope`` manually.
Usually you want to call it when your asyncio task or thread is shutting down.

Useful for storing the instance in the context of the current asyncio task or thread.
Can be used to create request-scoped dependencies in web applications.

User-defined scopes
-------------------

You can create your own scopes by subclassing the :class:`picodi.AutoScope` or
:class:`picodi.ManualScope` class. Usually you want to subclass the :class:`picodi.ManualScope`

Below you can see how :class:`picodi.SingletonScope` is implemented.
You can use it as a reference:

.. _singleton_scope_source:

.. literalinclude:: ../picodi/_scopes.py
   :pyobject: SingletonScope


Injecting async dependencies in sync dependants
-----------------------------------------------

Another powerful feature is the ability to use manually initialized async dependencies
in synchronous injections. While the values is stored in the context of the
scope you can inject it in sync code. Example:

.. code-block:: python

    import asyncio

    from picodi import Provide, SingletonScope, registry, inject


    @registry.set_scope(SingletonScope)
    async def get_async_dependency():
        return "from async"


    @inject
    def my_sync_service(async_dep=Provide(get_async_dependency)):
        return async_dep


    async def main():
        # Try to comment this lines below and see what happens
        registry.add_for_init(get_async_dependency)
        await registry.init()

        print(my_sync_service())


    asyncio.run(main())
    # Output: "from async"

Because ``get_async_dependency`` is ``SingletonScope`` scoped dependency and
it's initialized on startup, while your app is running you can inject it in sync code.


``lifespan`` decorator
***********************

You can use the :func:`picodi.registry.lifespan` and :func:`picodi.registry.alifespan`
decorators to manage the lifecycle of your dependencies.
It's convenient for using with workers or cli commands.

.. testcode::

    import asyncio

    from picodi import Provide, SingletonScope, registry, inject


    @registry.set_scope(SingletonScope, auto_init=True)
    def get_singleton():
        print("Creating singleton object")
        yield "singleton"
        print("Destroying singleton object")


    registry.add_for_init(get_singleton)


    @registry.lifespan()
    @inject
    def main(dep=Provide(get_singleton)):
        print(dep)


    main()
    # Output: Creating singleton object
    # Output: singleton
    # Output: Destroying singleton object


    # or async
    @registry.alifespan()
    @inject
    async def main(dep=Provide(get_singleton)):
        print(dep)


    asyncio.run(main())
    # Output: Creating singleton object
    # Output: singleton
    # Output: Destroying singleton object

.. testoutput::

    Creating singleton object
    singleton
    Destroying singleton object
    Creating singleton object
    singleton
    Destroying singleton object
