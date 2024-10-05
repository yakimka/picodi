Testing
=======

Overriding dependencies
-----------------------

Picodi aims to be a good citizen by providing a way to test your code. It
enables you to :doc:`override` dependencies in your tests, allowing you to replace
them with mocks or stubs as needed.

Picodi's lifespan in tests
--------------------------

For effective testing, it’s essential to have a clean environment for each test.
Picodi's scopes can introduce issues if not managed properly. To avoid this,
you should ensure that dependencies are properly teardown after each test.
In this example, we use the `pytest` framework, but the same principle applies
to other test frameworks.

.. testcode::

    # root conftest.py
    import pytest

    from picodi import shutdown_dependencies


    @pytest.fixture(autouse=True)
    async def _shutdown_picodi_dependencies():
        yield
        await shutdown_dependencies()


Detecting dependency usage
--------------------------

Sometimes, you need to know whether a particular dependency was used during a test so
that you can run cleanup logic.
For example, you may need to clear database tables, collections, etc., after each test.
While it's possible to write a custom dependency with teardown logic and override it
in tests, this approach is not always convenient.

Picodi provides a way to detect if a dependency was used in a test. For example:

You have a MongoDB dependency, and you want to drop the test database during the teardown.

.. code-block:: python

    # deps.py
    import os

    from picodi import inject, Provide
    from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase


    @inject
    def get_mongo_client() -> AsyncIOMotorClient:
        uri = os.environ["MONGO_URI"]
        return AsyncIOMotorClient(uri)


    def get_mongo_database_name() -> str:
        return "prod_db"


    @inject
    def get_mongo_database(
        mongo_client: AsyncIOMotorClient = Provide(get_mongo_client),
        database_name: str = Provide(get_mongo_database_name),
    ) -> AsyncIOMotorDatabase:
        return getattr(mongo_client, database_name)


.. testcode::

    # root conftest.py
    import pytest
    from uuid import uuid4

    from picodi import registry
    from picodi.helpers import enter

    # from deps import get_mongo_database, get_mongo_client, get_mongo_database_name


    # Use a different collection for each test to avoid conflicts
    @pytest.fixture()
    def mongo_test_db_name():
        return f"test_db_{uuid4().hex}"


    # Override the MongoDB database name for tests
    @pytest.fixture(autouse=True)
    async def _override_deps_for_tests(mongo_test_db_name):
        with registry.override(get_mongo_database_name, lambda: mongo_test_db_name):
            yield


    @pytest.fixture(autouse=True)
    async def _drop_mongo_database(mongo_test_db_name):
        yield
        # If the `get_mongo_database` dependency was used, this block will execute,
        # and the test database will be dropped during teardown
        if get_mongo_database in registry.touched:
            async with enter(get_mongo_client) as mongo_client:
                await mongo_client.drop_database(mongo_test_db_name)

        # Clear touched dependencies after each test.
        # This is important to properly detect dependency usage.
        registry.clear_touched()
