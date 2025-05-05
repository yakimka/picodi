.. _tutorial_async_dependencies:

########################################
Tutorial: 04 - Asynchronous Dependencies
########################################

Modern Python applications often rely on asynchronous operations for I/O-bound tasks like network
requests or database interactions. Picodi fully supports asynchronous dependencies and injection.

***************************
Defining Async Dependencies
***************************

Defining an asynchronous dependency is as simple as using ``async def`` for your dependency provider function.

Let's create an async dependency that simulates fetching user data from an external service:

.. testcode:: async_deps

    # dependencies.py
    import asyncio


    async def fetch_data() -> dict:
        """Simulates fetching data asynchronously."""
        print("Async Dep: Starting fetch")
        await asyncio.sleep(0.1)  # Simulate network delay
        print("Async Dep: Finished fetch")
        return {"data": "Data"}

****************************
Injecting Async Dependencies
****************************

If a function needs to inject an *asynchronous* dependency, that function itself **must**
also be ``async def``. Picodi needs an async context (``await``) to resolve the async dependency.

Let's create an async service function that uses our ``fetch_data`` dependency:

.. testcode:: async_deps

    # services.py
    from picodi import Provide, inject
    from dependencies import fetch_data


    @inject
    async def process_user(
        data: dict = Provide(fetch_data),  # Provide the async dep
    ) -> None:
        """Processes user data fetched asynchronously."""
        print("Async Service: Processing data")
        # ... further processing
        print(f"Async Service: Finished processing data: {data}")

******************
Running Async Code
******************

To run our async service, we need an event loop, typically using ``asyncio.run()``:

.. testcode:: async_deps

    # main.py
    import asyncio
    from services import process_user

    print("Main: Running async service.")
    asyncio.run(process_user())
    print("Main: Async service finished.")

**Output:**

.. testoutput:: async_deps

    Main: Running async service.
    Async Dep: Starting fetch
    Async Dep: Finished fetch
    Async Service: Processing data
    Async Service: Finished processing data: {'data': 'Data'}
    Main: Async service finished.

Picodi correctly awaited the ``fetch_data`` coroutine before
injecting the result into ``process_user``.

************************
Async Yield Dependencies
************************

Just like synchronous dependencies, async dependencies can use ``yield`` for setup
and teardown, often involving async operations.
This is similar to using :func:`python:contextlib.asynccontextmanager`.

Let's define an async dependency managing a (simulated) async database connection:

.. testcode:: async_yield_deps

    # dependencies.py
    import asyncio


    # Assume this is an async context manager for a DB connection pool
    class AsyncDbConnection:
        async def __aenter__(self):
            print("Async Yield Dep: Connecting to DB...")
            await asyncio.sleep(0.05)
            print("Async Yield Dep: Connected.")
            return self

        async def __aexit__(self, exc_type, exc, tb):
            print("Async Yield Dep: Disconnecting from DB...")
            await asyncio.sleep(0.05)
            print("Async Yield Dep: Disconnected.")

        async def execute(self, query: str):
            print(f"Async Yield Dep: Executing query '{query}'")
            await asyncio.sleep(0.02)
            return "Query Result"


    async def get_db_connection():
        """Provides an async DB connection and ensures disconnection."""
        async with AsyncDbConnection() as connection:
            yield connection


    # services.py
    from picodi import Provide, inject
    from dependencies import get_db_connection, AsyncDbConnection


    @inject
    async def run_db_query(
        query: str,
        db_conn: AsyncDbConnection = Provide(get_db_connection),
    ) -> str:
        """Runs a query using an injected async database connection."""
        print("Async Service: Running DB query.")
        result = await db_conn.execute(query)
        print("Async Service: Query finished.")
        return result


    # main.py
    import asyncio
    from services import run_db_query

    print("Main: Running async DB service.")
    result = asyncio.run(run_db_query("SELECT * FROM users"))
    print(f"Main: Got result: {result}")
    print("Main: Async DB service finished.")


**Output:**

.. testoutput:: async_yield_deps

    Main: Running async DB service.
    Async Yield Dep: Connecting to DB...
    Async Yield Dep: Connected.
    Async Service: Running DB query.
    Async Yield Dep: Executing query 'SELECT * FROM users'
    Async Service: Query finished.
    Async Yield Dep: Disconnecting from DB...
    Async Yield Dep: Disconnected.
    Main: Got result: Query Result
    Main: Async DB service finished.

Picodi correctly handles the async setup (``__aenter__``) before injecting the ``db_conn``
and the async teardown (``__aexit__``) after ``run_db_query`` completes.

********************************
Scopes and Async Dependencies
********************************

Scopes like :class:`picodi.SingletonScope` work exactly the same way for async dependencies as they
do for sync ones. If we added ``@registry.set_scope(SingletonScope)`` to ``get_db_connection``,
the connection would be established only once and reused,
with disconnection happening only upon :func:`picodi.Registry.shutdown`.
Remember that ``registry.shutdown()`` returns an awaitable if there are async dependencies
to clean up, so you'd need ``await registry.shutdown()``.

***********
Next Steps
***********

You now know how to work with both sync and async dependencies.
The next crucial concept for building flexible and testable applications
is :ref:`Dependency Overrides <tutorial_dependency_overrides>`.
