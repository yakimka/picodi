.. _faq:

##########################
Frequently Asked Questions
##########################

Here are answers to some common questions about using Picodi.

*************************************************************************************************************************
Q: I'm injecting an `async def` dependency into a `def` function, but I get a coroutine object instead of the value. Why?
*************************************************************************************************************************

**A:** Synchronous functions (`def`) cannot `await` asynchronous operations. When you try to `Provide` an `async def` dependency into a sync function, Picodi cannot await the dependency provider to get its result within the synchronous context. Therefore, it injects the awaitable coroutine object itself.

To correctly use the result of an async dependency, the function *consuming* it must also be `async def`.

The exception to this is when using :ref:`pre-initialized async dependencies with manual scopes <topics_async_in_sync>`. If an async dependency using `SingletonScope` (or another manual scope) is initialized beforehand using `await registry.init()`, its *cached value* can then be injected into synchronous functions because Picodi retrieves the already-computed value from the cache.

*******************************************************************************
Q: When should I use `SingletonScope` vs. `NullScope`?
*******************************************************************************

**A:**

*   Use **`SingletonScope`** for dependencies that are:
    *   **Expensive to create:** Like database connection pools, HTTP client sessions, or complex configuration objects. Creating them only once improves performance.
    *   **Need to be shared globally:** When exactly one instance of a service or resource should be used throughout the application.
    *   **Stateful (with caution):** If a dependency needs to maintain state across different parts of your application (use carefully to avoid unexpected side effects).
    Remember that `SingletonScope` requires manual cleanup via `registry.shutdown()`.

*   Use **`NullScope`** (the default) for dependencies that are:
    *   **Cheap to create:** Simple functions, small data objects.
    *   **Stateless:** Dependencies whose instances don't carry state between calls.
    *   **Need to be unique per use:** When each injection must receive a completely new instance.
    Cleanup happens automatically after the injection point finishes.

*******************************************************************************
Q: Why do I need `registry.shutdown()`? When should I call it?
*******************************************************************************

**A:** `registry.shutdown()` is necessary to trigger the cleanup logic (the code after `yield` in generator dependencies) for dependencies managed by **manual scopes** (like `SingletonScope` and `ContextVarScope`).

Dependencies using `AutoScope` (like the default `NullScope`) clean themselves up automatically after the injecting function finishes. Manual scopes, however, persist their instances until explicitly told to shut down.

You should typically call `registry.shutdown()` **once** when your application is gracefully stopping.

*   For web applications, this might be during the ASGI application shutdown event.
*   For scripts or workers, it's usually at the very end of the main execution block.
*   The `registry.lifespan()` and `registry.alifespan()` context managers call `shutdown()` automatically upon exiting the context.

If you have asynchronous cleanup logic (async yield dependencies in manual scopes), you **must** `await registry.shutdown()`.

*******************************************************************************
Q: Can I use Picodi without type hints?
*******************************************************************************

**A:** Yes. Picodi's core injection mechanism relies on the `Provide()` marker in the default value, not on type hints. However, using type hints is **strongly recommended** for:

*   **Readability:** Makes it clear what type is expected or provided.
*   **Static Analysis:** Allows tools like MyPy to catch errors.
*   **Maintainability:** Makes the code easier to understand and refactor.

*******************************************************************************
Q: How does Picodi compare to FastAPI's built-in DI?
*******************************************************************************

**A:** FastAPI's DI is excellent and tightly integrated with route parameters, request data validation, and security. Picodi complements it rather than replacing it entirely.

*   **FastAPI DI excels at:** Handling request-specific data (path/query params, headers, bodies), security dependencies, and simple request-level dependencies.
*   **Picodi excels at:**
    *   Managing application-level services and resources with controlled lifecycles (**scopes** like `SingletonScope`).
    *   Sharing dependencies between FastAPI routes and other parts of your application (workers, CLI commands).
    *   Providing a consistent DI mechanism across different types of Python applications.
    *   Advanced testing scenarios using flexible overrides.

You can (and often should) use both together. Use FastAPI's `Depends` for request/route-level concerns and Picodi's `Provide` (especially `Provide(..., wrap=True)`) for injecting application services or shared resources managed by Picodi. See :ref:`topics_integrations` for examples.

*******************************************************************************
Q: My tests are failing because of state leaking between them. What's wrong?
*******************************************************************************

**A:** This usually happens due to:

1.  **Unmanaged Singletons:** If you use `SingletonScope` dependencies in tests but don't properly clean them up, their state persists across tests.
2.  **Persistent Overrides:** If you apply overrides using the decorator (`@registry.override(...)`) or direct calls (`registry.override(...)`) but forget to clear them after the test.

**Solutions:**

*   **Use the Picodi Pytest Plugin:** Add `picodi.integrations._pytest` (and `_pytest_asyncio` if needed) to your `conftest.py`. It automatically calls `registry.shutdown()`, `registry.clear_overrides()`, and `registry.clear_touched()` after each test.
*   **Manual Cleanup (if not using the plugin):** Ensure your test teardown logic (e.g., in `pytest` fixtures or `tearDown` methods) explicitly calls `registry.shutdown()` and `registry.clear_overrides()`.
*   **Prefer Context Managers for Overrides:** Use `with registry.override(...):` within tests, as it automatically clears the override upon exiting the block.

********************************************************************************************************************************
Q: flake8-bugbear complains about `B008 Do not perform function calls in argument defaults` when using `Provide`. How to fix it?
********************************************************************************************************************************

**A:** You need to tell `flake8-bugbear` that `picodi.Provide` is safe to use in defaults. Add or modify the `extend-immutable-calls` setting in your flake8 configuration file (e.g., `setup.cfg`, `tox.ini`, or `.flake8`):

.. code-block:: ini

    [flake8]
    # ... other settings ...
    extend-immutable-calls = picodi.Provide, Provide

This informs the linter that `Provide` itself doesn't execute the dependency immediately but acts as a marker.
