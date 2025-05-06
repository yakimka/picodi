.. _topics_dependencies:

######################
Dependencies Explained
######################

In Picodi, the concept of a "dependency" is intentionally simple: **a dependency provider is typically
a Python function (or any callable) that returns a value or yields it.**
This function usually takes no required arguments, allowing Picodi to call it automatically when needed.

This topic delves into the different ways you can define these dependency providers.

***************************
Simple Dependency Functions
***************************

The most basic form of a dependency provider is a function that directly returns a value.

**Synchronous Example:**

.. code-block:: python

    def get_database_url() -> str:
        """Returns the connection string for the database."""
        return "postgresql://user:password@host:port/dbname"


    def get_settings() -> dict:
        """Loads and returns application settings."""
        # In a real app, this might load from a file or environment variables
        return {"timeout": 30, "retries": 3}

**Asynchronous Example:**

Picodi also supports asynchronous dependency providers.
These are defined using the ``async def`` syntax.

.. code-block:: python

    import asyncio


    async def get_external_api_key() -> str:
        """Fetches an API key from a secure vault (simulated)."""
        print("Fetching API key...")
        await asyncio.sleep(0.1)  # Simulate I/O
        return "secret-api-key-12345"

These functions are ready to be used with :func:`~picodi.Provide`
within an :func:`~picodi.inject`-decorated function.

****************************************
Yield Dependencies (Resource Management)
****************************************

Often, dependencies represent resources that need setup before use and cleanup afterward
(e.g., database connections, file handles, network clients).
Picodi handles this elegantly using generator functions with a single ``yield``.

Picodi treats such generators like context managers:

1.  **Setup:** Code before ``yield`` runs when the dependency is first requested.
2.  **Value:** The value yielded is injected into the dependent function.
3.  **Teardown:** Code after ``yield`` (ideally in a ``finally`` block) runs after the
    dependent function finishes execution (or when the dependency's scope dictates cleanup).

**Synchronous Example:**

.. code-block:: python

    import sqlite3


    def get_db_cursor():
        """Provides a database cursor and ensures the connection is closed."""
        connection = sqlite3.connect(":memory:")
        print("DB Connection Opened")
        cursor = connection.cursor()
        try:
            yield cursor  # Provide the cursor
        finally:
            connection.close()
            print("DB Connection Closed")

**Asynchronous Example:**

.. code-block:: python

    import asyncio


    class AsyncResource:  # Example async resource
        async def setup(self):
            print("Async Resource Setup")
            await asyncio.sleep(0.05)
            return self

        async def close(self):
            print("Async Resource Closed")
            await asyncio.sleep(0.05)

        async def do_work(self):
            print("Async Resource Working")


    async def get_async_resource():
        """Provides an async resource with setup and teardown."""
        resource = AsyncResource()
        await resource.setup()
        try:
            yield resource
        finally:
            await resource.close()

These yield dependencies ensure resources are managed correctly within the scope of their usage.
The exact timing of the teardown depends on the :ref:`scope <topics_scopes>` assigned to the dependency.

*************************************
Dependencies Using Other Dependencies
*************************************

Dependency provider functions can themselves use :func:`~picodi.inject` and :func:`~picodi.Provide`
to depend on other dependencies. Picodi automatically resolves the entire dependency graph.

.. code-block:: python

    from picodi import Provide, inject


    def get_base_url() -> str:
        return "https://config-service.com"


    @inject  # get_api_config depends on get_base_url
    def get_api_config(url: str = Provide(get_base_url)) -> dict:
        print(f"Fetching config from {url}")
        # Simulate fetching config based on the URL
        return {"key": "config-key", "timeout": 5}


    # Another function can now depend on get_api_config
    # @inject
    # def use_config(config: dict = Provide(get_api_config)):
    #     api_key = config["key"]
    #     # ...

Picodi ensures ``get_base_url`` is resolved first, its result is passed to ``get_api_config``,
and then the result of ``get_api_config`` is available for injection elsewhere.

*************
Key Takeaways
*************

*   A Picodi dependency provider is typically a zero-argument callable (often a function).
*   Use regular functions for simple value dependencies (sync or async).
*   Use generator functions with a single ``yield`` for dependencies requiring setup/teardown (sync or async).
*   Dependencies can depend on other dependencies using ``@inject`` and ``Provide``.

Next, let's look at how these dependencies are actually provided to your code using :ref:`Injection <topics_injection>`.
