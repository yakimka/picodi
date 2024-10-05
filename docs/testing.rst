Testing
=======

Overriding Dependencies
-----------------------

Picodi aims to be a good citizen by providing a way to test your code. It
enables you to :doc:`overriding` in your tests, allowing you to replace
them with mocks or stubs as needed.

Picodi's Lifespan in Tests
--------------------------

For effective testing, it’s essential to maintain a clean environment for each test.
Picodi's scopes can introduce issues if not managed properly. To prevent this,
ensure that dependencies are properly torn down after each test.
In this example, we showcase example of pseudo framework,
but you can adapt it to your testing framework.

.. testcode::

    from picodi import shutdown_dependencies


    async def teardown_hook():
        await shutdown_dependencies()


Detecting Dependency Usage
--------------------------

Sometimes, you need to know whether a particular dependency was used during a test so
that you can run cleanup logic afterward.
For example, you may need to clear database tables, collections, etc., after each test.
While it is possible to write a custom dependency with teardown logic and override it
in tests, this approach is not always convenient.

Picodi provides a way to detect if a dependency was used in a test. For instance:

You have a MongoDB dependency, and you want to drop the test database during teardown.

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

    from picodi import registry
    from picodi.helpers import enter

    # from deps import get_mongo_database, get_mongo_client, get_mongo_database_name


    # Override MongoDB database name for tests
    async def setup_hook():
        with registry.override(get_mongo_database_name, lambda: "test_db"):
            yield


    async def teardown_hook(mongo_test_db_name):
        # If the `get_mongo_database` dependency was used, this block will execute,
        # and the test database will be dropped during teardown.
        if get_mongo_database in registry.touched:
            async with enter(get_mongo_client) as mongo_client:
                await mongo_client.drop_database(mongo_test_db_name)

        # Clear touched dependencies after each test to ensure correct detection
        registry.clear_touched()


Pytest Integration
------------------

Picodi provides a built-in ``pytest`` plugin that simplifies the process of
managing dependencies in your tests.

Setting Up the Pytest Plugin
****************************

To use Picodi's built-in plugin for pytest,
add the following to the root ``conftest.py`` of your project:

.. code-block:: python

    # conftest.py
    pytest_plugins = [
        "picodi.integrations._pytest",
        # If you use asyncio in your tests, add the following plugin as well.
        # It must be added after the main plugin.
        "picodi.integrations._pytest_asyncio",
    ]

To use the ``_pytest_asyncio`` plugin, you need to install the
`pytest-asyncio <https://pypi.org/project/pytest-asyncio/>`_ package.

Now, Picodi will automatically handle dependency shutdown and cleanup for you.

Override Marker
***************

You can use the ``picodi_override`` marker to override dependencies in your tests.

.. code-block:: python

    @pytest.mark.picodi_override(original_dependency, override_dependency)
    def test_foo():
        pass


    # Or for multiple dependencies at once:
    @pytest.mark.picodi_override(
        [
            (original_dependency, override_dependency),
            (second_original_dependency, second_override_dependency),
        ]
    )
    def test_bar():
        pass


Example
*******

The previous examples can be rewritten as:

.. code-block:: python

    import pytest

    from picodi import registry
    from picodi.helpers import enter

    # from deps import get_mongo_database, get_mongo_client, get_mongo_database_name

    pytestmark = pytest.mark.picodi_override(get_mongo_database_name, lambda: "test_db")

    # `shutdown_dependencies` is called automatically after each test


    @pytest.fixture(autouse=True)
    async def _drop_mongo_database():
        yield
        # If the `get_mongo_database` dependency was used, this block will execute,
        # and the test database will be dropped during teardown.
        if get_mongo_database in registry.touched:
            async with enter(get_mongo_client) as mongo_client:
                await mongo_client.drop_database("test_db")

        # `registry.clear_touched()` is called automatically after each test
