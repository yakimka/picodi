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
In this example, we use the ``pytest`` framework, but the same principle applies
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

    from picodi import registry
    from picodi.helpers import enter

    # from deps import get_mongo_database, get_mongo_client, get_mongo_database_name


    # Override the MongoDB database name for tests
    @pytest.fixture(autouse=True)
    async def _override_deps_for_tests():
        with registry.override(get_mongo_database_name, lambda: "test_db"):
            yield


    @pytest.fixture(autouse=True)
    async def _drop_mongo_database():
        yield
        # If the `get_mongo_database` dependency was used, this block will execute,
        # and the test database will be dropped during teardown
        if get_mongo_database in registry.touched:
            async with enter(get_mongo_client) as mongo_client:
                await mongo_client.drop_database("test_db")

        # Clear touched dependencies after each test.
        # This is important to properly detect dependency usage.
        registry.clear_touched()


Pytest integration
------------------

Section above shows how to integrate Picodi with `pytest` by yourself. However, Picodi
provides a built-in ``pytest`` plugin that simplifies the process.

Setup pytest plugin
********************

To use builtin Picodi plugin for pytest you need to add to root conftest.py of your project:

.. code-block:: python

    # conftest.py
    pytest_plugins = [
        "picodi.integrations._pytest",
        # If you use asyncio in your tests, add also the following plugin,
        # it needs to be added after the main plugin.
        "picodi.integrations._pytest_asyncio",
    ]

For using ``_pytest_asyncio`` plugin you need to install
`pytest-asyncio <https://pypi.org/project/pytest-asyncio/>`_ package.

Now Picodi will automatically handle dependency shutdown and cleanup for you.

Override marker
****************

You can use ``picodi_override`` marker to override dependencies in your tests.

.. code-block:: python

    @pytest.mark.picodi_override(original_dependency, override_dependency)
    def test_foo(): ...


    # or for multiple dependencies at once
    @pytest.mark.picodi_override(
        [
            (original_dependency, override_dependency),
            (second_original_dependency, second_override_dependency),
        ]
    )
    def test_bar(): ...


Example
********

So previous example can be rewritten as:

.. code-block:: python

    # root conftest.py
    import pytest

    from picodi import registry
    from picodi.helpers import enter

    # from deps import get_mongo_database, get_mongo_client, get_mongo_database_name

    pytestmark = pytest.mark.picodi_override(get_mongo_database_name, lambda: "test_db")


    @pytest.fixture(autouse=True)
    async def _drop_mongo_database():
        yield
        # If the `get_mongo_database` dependency was used, this block will execute,
        # and the test database will be dropped during teardown
        if get_mongo_database in registry.touched:
            async with enter(get_mongo_client) as mongo_client:
                await mongo_client.drop_database("test_db")
