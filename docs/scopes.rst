Scopes
======

Resolving dependency values and injecting them is a good start, but it's not enough.
We need to be able to control the lifetime of the objects we create. This is where scopes come in.

Picodi has two types of scopes: auto and manual. Lifecycle of auto scopes is managed
by the Picodi itself, auto-scopes will be initialized and closed automatically.
Manual scopes initialized on first injection or when :func:`picodi.init_dependencies`
is called by the user and closed when :func:`picodi.shutdown_dependencies` is called.

To set the scope for a dependency, you can use the :func:`picodi.dependency` decorator
with the ``scope_class`` argument. Example:

.. code-block:: python

    from picodi import dependency, SingletonScope

    @dependency(scope_class=SingletonScope)
    def get_singleton():
        return object()

Built-in scopes
---------------

NullScope
*********

By default, all dependencies are created with the :class:`picodi.NullScope` scope.
This means that a new instance is created every time the dependency is injected
and closed immediately after root injection is done.

SingletonScope
**************

The :class:`picodi.SingletonScope` scope creates a single instance of the dependency
and reuses it every time the dependency is injected. The instance is created when the
dependency is first injected or :func:`picodi.init_dependencies` is called.

``SingletonScope`` is the manual scope, so you need to call :func:`picodi.shutdown_dependencies`
manually. Usually you want to call it when your application is shutting down.

ContextVarScope
***************

The :class:`picodi.ContextVarScope` uses the :class:`python:contextvars.ContextVar`
to store the instance. The instance is created when the
dependency is first injected or :func:`picodi.init_dependencies` is called.

``ContextVarScope`` is the manual scope, so you need to call :func:`picodi.shutdown_dependencies`
manually. Usually you want to call it when your asyncio task or thread is shutting down.

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

Lifecycle of manual scopes
--------------------------

You can manually initialize your dependencies by calling :func:`picodi.init_dependencies`.
It will initialize all dependencies with manual scopes. This can be useful when you want to
initialize your dependencies on application startup.

Also, you need to manually close your dependencies by calling
:func:`picodi.shutdown_dependencies`.

Injecting async dependencies in sync dependants
***********************************************

One even more useful feature is that if you manually initialize your async dependencies
you can use them in sync injections. While the values is stored in the context of the
scope you can inject it in sync code. Example:

.. code-block:: python

    import asyncio
    from picodi import dependency, SingletonScope, init_dependencies, Provide, inject

    @dependency(scope_class=SingletonScope)
    async def get_async_dependency():
        return "from async"

    @inject
    def my_sync_service(async_dep=Provide(get_async_dependency)):
        return async_dep

    async def main():
        await init_dependencies()  # Try to comment this line and see what happens

        print(my_sync_service())

    asyncio.run(main())
    # Output: "from async"

Because ``get_async_dependency`` is ``SingletonScope`` scoped dependency and
it's initialized on startup, while your app is running you can inject it in sync code.

Skipping manual initialization
******************************

If you want to skip manual initialization of your dependency you can use the
``ignore_manual_init`` argument of the :func:`picodi.dependency` decorator.

.. code-block:: python

    from picodi import dependency, SingletonScope, init_dependencies

    # Try to set `ignore_manual_init` to `False` and see what happens
    @dependency(scope_class=SingletonScope, ignore_manual_init=True)
    def get_dependency():
        print("This will not be printed")
        return "from async"

    init_dependencies()  # This will not initialize get_dependency

Managing scopes selectively
***************************

By default :func:`picodi.init_dependencies` and :func:`picodi.shutdown_dependencies`
will initialize and close all dependencies with manual scopes. If you want to manage
scopes selectively you can use the ``scope_class`` argument of these functions.

.. code-block:: python

    from picodi import init_dependencies, shutdown_dependencies, SingletonScope

    init_dependencies(scope_class=SingletonScope)
    # Only SingletonScope dependencies will be initialized

    shutdown_dependencies(scope_class=SingletonScope)
    # Only SingletonScope dependencies will be closed

In the example above, only dependencies with the ``SingletonScope`` scope will be managed,
``ContextVarScope`` scoped dependencies or dependencies with user-defined scopes
will be ignored. If you want to manage multiple scopes, you can pass a tuple of scopes.

.. code-block:: python

    from picodi import init_dependencies, shutdown_dependencies, SingletonScope, ContextVarScope

    init_dependencies(scope_class=(SingletonScope, ContextVarScope))
    # SingletonScope and ContextVarScope dependencies will be initialized

    shutdown_dependencies(scope_class=(SingletonScope, ContextVarScope))
    # SingletonScope and ContextVarScope dependencies will be closed