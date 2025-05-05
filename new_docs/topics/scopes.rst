.. _topics_scopes:

######################
Scopes
######################

While resolving dependency values and injecting them is a good starting point, it's often insufficient on its own. We also need control over the **lifecycle** of the objects we create – when they are created, how long they persist, and when they are cleaned up. This is where **scopes** come in.

Scopes in Picodi determine the lifespan and caching behavior of dependency instances.

********************************
Assigning Scopes to Dependencies
********************************

You assign a scope to a dependency provider function using the :meth:`picodi.Registry.set_scope` decorator provided by the `picodi.registry` object.

.. code-block:: python

    from picodi import registry, SingletonScope, Provide, inject

    @registry.set_scope(SingletonScope) # Assign SingletonScope here
    def get_shared_resource():
        print("Creating shared resource...")
        # Imagine this is an expensive object like a DB connection pool
        resource = {"id": "singleton_resource"}
        yield resource # Use yield for potential cleanup
        print("Cleaning up shared resource...")

    @inject
    def use_resource_1(res = Provide(get_shared_resource)):
        print(f"User 1 using resource: {res['id']}")

    @inject
    def use_resource_2(res = Provide(get_shared_resource)):
        print(f"User 2 using resource: {res['id']}")

    # --- Application Code ---
    print("First use:")
    use_resource_1()
    print("\nSecond use:")
    use_resource_2()

    print("\nShutting down:")
    # SingletonScope requires manual shutdown for cleanup
    registry.shutdown()

**Output:**

.. code-block:: text

    First use:
    Creating shared resource...
    User 1 using resource: singleton_resource

    Second use:
    User 2 using resource: singleton_resource

    Shutting down:
    Cleaning up shared resource...

As you can see, "Creating shared resource..." happened only once. The same instance was reused. Cleanup happened only at `registry.shutdown()`.

If you remove the `@registry.set_scope(SingletonScope)` decorator, Picodi will use the default `NullScope`, and the resource would be created and cleaned up for *each* call to `use_resource_1` and `use_resource_2`.

********************************
Built-in Scopes
********************************

Picodi comes with several built-in scopes:

`NullScope` (Default)
=====================
*   **Class:** :class:`picodi.NullScope`
*   **Behavior:** Creates a new instance every time the dependency is injected. No caching occurs.
*   **Cleanup (Yield Dependencies):** Runs immediately after the injecting function finishes.
*   **Use Case:** Suitable for very cheap-to-create dependencies or those that *must* be unique per injection. This is the default scope if none is specified via `@registry.set_scope`.

`SingletonScope`
================
*   **Class:** :class:`picodi.SingletonScope`
*   **Behavior:** Creates a single instance the first time the dependency is requested. This instance is cached globally and reused for all subsequent requests for that dependency across the application.
*   **Cleanup (Yield Dependencies):** Runs only when :meth:`picodi.Registry.shutdown` is called (typically at application exit).
*   **Use Case:** Ideal for expensive-to-create objects that should be shared globally, like configuration objects, database connection pools, or HTTP clients.

`ContextVarScope`
=================
*   **Class:** :class:`picodi.ContextVarScope`
*   **Behavior:** Caches instances within a :class:`python:contextvars.ContextVar`. This means the instance's lifetime is tied to the current context, making it suitable for scenarios like web requests in async frameworks or thread-local storage. A different context (e.g., a different web request or thread) will get its own instance.
*   **Cleanup (Yield Dependencies):** Runs only when :meth:`picodi.Registry.shutdown` is called *specifically for this scope* (i.e., `registry.shutdown(scope_class=ContextVarScope)`). This is often done at the end of a request or task.
*   **Use Case:** Request-scoped dependencies in web applications (see :ref:`topics_integrations`), thread-local dependencies.

********************************
Manual vs. Auto Scopes
********************************

Scopes in Picodi inherit from either `ManualScope` or `AutoScope`.

*   **`ManualScope`** (like `SingletonScope`, `ContextVarScope`): Require explicit cleanup via :meth:`~picodi.Registry.shutdown`. Their instances persist until shutdown is called for their scope class (or all manual scopes if no class is specified).
*   **`AutoScope`** (like `NullScope`): Cleanup happens automatically after the root injection point finishes. You don't need to call `shutdown` for these.

****************************************
Automatic Initialization (``auto_init``)
****************************************

When setting a scope, especially a manual one like `SingletonScope`, you might want the dependency to be created proactively when the application starts, rather than waiting for the first request. You can achieve this using the `auto_init=True` parameter in `@registry.set_scope`.

.. code-block:: python

    from picodi import registry, SingletonScope

    @registry.set_scope(SingletonScope, auto_init=True) # Note auto_init
    def get_eager_singleton():
        print("Eager singleton created!")
        return "I was created early"

    # At application startup:
    print("Calling registry.init()...")
    registry.init() # This will initialize all 'auto_init=True' dependencies
    print("registry.init() finished.")

    # Later, when injected:
    # @inject
    # def use_eager(dep=Provide(get_eager_singleton)):
    #     print(f"Using dependency: {dep}")
    #
    # use_eager() # Will not print "Eager singleton created!" again

**Output:**

.. code-block:: text

    Calling registry.init()...
    Eager singleton created!
    registry.init() finished.

Dependencies marked with `auto_init=True` will be initialized when :meth:`picodi.Registry.init` is called. You can also explicitly add dependencies to be initialized using :meth:`picodi.Registry.add_for_init`. See :ref:`topics_lifespan` for more details on `init` and `shutdown`.

********************************
User-defined Scopes
********************************

You can create custom scopes by subclassing :class:`picodi.ManualScope` or :class:`picodi.AutoScope` and implementing the required methods (`get`, `set`, `enter`, `shutdown`). This allows for fine-grained control over dependency lifecycles if the built-in scopes don't meet your specific needs. Consult the API Reference (once available) for details on the `Scope` base classes.

****************
Key Takeaways
****************

*   Scopes control the lifecycle (creation, caching, cleanup) of dependency instances.
*   Use `@registry.set_scope(ScopeClass)` to assign a scope to a dependency provider.
*   `NullScope` (default): New instance per injection, immediate cleanup.
*   `SingletonScope`: One instance globally, manual cleanup via `registry.shutdown()`.
*   `ContextVarScope`: Instance per context (request/thread), manual cleanup via `registry.shutdown(scope_class=ContextVarScope)`.
*   Use `auto_init=True` with `@registry.set_scope` and call `registry.init()` for eager initialization.

Next, let's explore how to replace dependencies at runtime using :ref:`Overrides <topics_overriding>`.
