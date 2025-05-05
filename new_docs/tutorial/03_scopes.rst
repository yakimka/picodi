.. _tutorial_scopes:

########################
Tutorial: 03 - Scopes
########################

In the previous steps, you might have noticed that our dependency functions (like `get_api_base_url` or `get_temp_file_path`) were executed *every time* they were needed by an injected function. This is the default behavior, but often not what you want, especially for expensive resources like database connections or configuration objects that should only be created once.

Picodi uses **Scopes** to control the lifecycle and caching of dependency instances.

****************
What are Scopes?
****************

A scope defines:

1.  **When** a new instance of a dependency is created.
2.  **Where** the created instance is stored (cached).
3.  **How long** the instance lives before it's potentially discarded or cleaned up.

********************************
Default Scope: `NullScope`
********************************

By default, all dependencies use `picodi.NullScope`.

*   **Lifecycle:** A new instance is created *every single time* the dependency is injected.
*   **Caching:** No caching occurs.
*   **Cleanup (for yield dependencies):** Cleanup code (after `yield`) runs immediately after the function that injected the dependency finishes.

This explains the output in the previous steps where we saw "Creating API base URL dependency" or the temp file setup/teardown messages multiple times. `NullScope` is suitable for dependencies that are very cheap to create or must be unique for each use.

********************************
Singleton Scope: `SingletonScope`
********************************

A very common requirement is to have a single instance of a dependency shared across the entire application (or for its entire lifetime). This is known as the Singleton pattern. Picodi provides `picodi.SingletonScope` for this.

*   **Lifecycle:** An instance is created *only the first time* the dependency is requested.
*   **Caching:** The created instance is stored globally (within the Picodi registry).
*   **Cleanup (for yield dependencies):** Cleanup code runs *only when explicitly triggered*, typically at application shutdown.

********************************
Setting a Dependency's Scope
********************************

To assign a scope other than the default `NullScope`, you use the `@registry.set_scope` decorator on your dependency *provider* function.

Let's apply `SingletonScope` to our `get_temp_file_path` dependency from the previous step:

.. testcode:: scopes

    # dependencies.py
    import tempfile
    import os
    from contextlib import contextmanager
    from picodi import registry, SingletonScope # Import registry and SingletonScope

    @registry.set_scope(SingletonScope) # Set the scope here!
    @contextmanager
    def get_temp_file_path():
        """Provides a path to a temporary file and cleans it up afterwards."""
        tf = tempfile.NamedTemporaryFile(delete=False, mode='w+', suffix=".txt")
        file_path = tf.name
        print(f"Setup: Created temp file: {file_path}")
        tf.close()

        try:
            yield file_path
        finally:
            if os.path.exists(file_path):
                os.remove(file_path)
                print(f"Teardown: Removed temp file: {file_path}")
            else:
                print(f"Teardown: Temp file already removed: {file_path}")

    # services.py
    # (write_to_temp_file remains the same)
    from picodi import Provide, inject
    from dependencies import get_temp_file_path

    @inject
    def write_to_temp_file(
        content: str,
        temp_file: str = Provide(get_temp_file_path)
    ) -> None:
        """Writes content to a temporary file provided by a dependency."""
        print(f"Service: Writing to {temp_file}")
        with open(temp_file, "a") as f:
            f.write(content + "\n")
        print(f"Service: Finished writing to {temp_file}")

    # main.py
    from services import write_to_temp_file
    from picodi import registry # Import registry for shutdown

    print("Main: Calling service the first time.")
    write_to_temp_file("Singleton message 1!")
    print("Main: Service call finished.")

    print("\nMain: Calling service the second time.")
    write_to_temp_file("Singleton message 2!")
    print("Main: Service call finished.")

    print("\nMain: Manually shutting down SingletonScope dependencies.")
    # For manual scopes like SingletonScope, cleanup must be triggered.
    registry.shutdown()
    print("Main: Shutdown complete.")

**Explanation:**

1.  **`@registry.set_scope(SingletonScope)`:** We decorated `get_temp_file_path` to tell Picodi it should be managed by `SingletonScope`.
2.  **`registry.shutdown()`:** Because `SingletonScope` doesn't clean up automatically after each injection, we need to call `registry.shutdown()` at the end of our application's life to trigger the teardown code (the `finally` block in `get_temp_file_path`).

**Output:**

.. testoutput:: scopes

    Main: Calling service the first time.
    Setup: Created temp file: .../tmp....txt
    Service: Writing to .../tmp....txt
    Service: Finished writing to .../tmp....txt
    Main: Service call finished.

    Main: Calling service the second time.
    Service: Writing to .../tmp....txt
    Service: Finished writing to .../tmp....txt
    Main: Service call finished.

    Main: Manually shutting down SingletonScope dependencies.
    Teardown: Removed temp file: .../tmp....txt
    Main: Shutdown complete.

Look closely at the output:

*   "Setup: Created temp file..." appears only **once**, during the first call to `write_to_temp_file`.
*   On the second call, the existing file path (cached by `SingletonScope`) is reused directly. No setup code runs.
*   "Teardown: Removed temp file..." appears only **once** at the very end, after we explicitly called `registry.shutdown()`.

This demonstrates how `SingletonScope` creates a single, long-lived instance and defers cleanup until explicitly requested.

********************************
Other Built-in Scopes
********************************

Picodi also provides `ContextVarScope` which is useful in asynchronous contexts (like web frameworks) to scope dependencies to a specific task or request. You can also create your own custom scopes. We'll touch on `ContextVarScope` briefly when discussing :ref:`integrations <topics_integrations>`.

***********
Next Steps
***********

We've covered synchronous dependencies and scopes. Now let's see how Picodi handles :ref:`Asynchronous Dependencies <tutorial_async_dependencies>`.
