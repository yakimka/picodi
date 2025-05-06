.. _topics_testing:

###################
Testing with Picodi
###################

One of the primary motivations for using Dependency Injection is to improve the **testability** of your code.
Picodi makes it easy to replace real dependencies with mocks, stubs, or test doubles during testing,
allowing you to write isolated and reliable tests.

********************************
The Role of Dependency Overrides
********************************

The core feature enabling testing is :ref:`dependency overriding <topics_overriding>`.
By overriding a dependency provider (like one that connects to a real database or external API),
you can substitute it with a controlled, predictable alternative within your tests.

*************************
Manual Overrides in Tests
*************************

You can directly use ``registry.override`` as a context manager within your test functions.
This is useful for simple cases or when not using a testing framework with specific Picodi integration.

.. code-block:: python

    # test_example.py
    from picodi import registry, Provide, inject


    # --- Production Code ---
    def get_live_api_client():
        print("PROD: Creating live API client")
        # ... returns a real client ...
        return "RealApiClient"


    @inject
    def process_data_from_api(client=Provide(get_live_api_client)):
        print(f"SERVICE: Processing using {client}")
        # ... uses client ...
        return f"Data processed by {client}"


    # --- Test Code ---
    def get_mock_api_client():
        print("TEST: Creating mock API client")
        return "MockApiClient"


    def test_process_data_with_mock():
        print("\nTEST: Starting test_process_data_with_mock")
        # Use override as context manager
        with registry.override(get_live_api_client, get_mock_api_client):
            print("TEST: Calling service within override context")
            result = process_data_from_api()
            assert result == "Data processed by MockApiClient"
        print("TEST: Exited override context (override cleared)")


    # Run with: pytest test_example.py -s

Remember to manage cleanup if your overrides involve dependencies with manual scopes,
although using the context manager handles clearing the override itself.

******************
Pytest Integration
******************
.. _topics_pytest_integration:

Picodi provides a dedicated ``pytest`` plugin that significantly simplifies testing workflows
by automating setup and cleanup.

Setup
=====
To enable the plugin, add it to your project's root ``conftest.py`` file:

.. code-block:: python

    # conftest.py
    pytest_plugins = [
        "picodi.integrations._pytest",
        # If you use asyncio in your tests, add the following plugin as well.
        # It must be added after the main plugin.
        # "picodi.integrations._pytest_asyncio",
    ]

Automatic Cleanup
=================
Once the plugin is active, it automatically performs the following cleanup actions **after each test** function finishes:

*   :meth:`~picodi.Registry.shutdown`: Ensures that any manual-scoped dependencies
    (like :class:`~picodi.SingletonScope` or :class:`~picodi.ContextVarScope`)
    that were used during the test have their cleanup logic (e.g., ``finally`` blocks in yield dependencies) executed.
*   :meth:`~picodi.Registry.clear_overrides`: Removes all overrides that might have been set during the test, ensuring a clean state
    for the next test.
*   Clears the internal set of "touched" dependencies. This is an advanced feature related to
    tracking which dependencies were resolved, and clearing it ensures test isolation.

This automatic cleanup is crucial for maintaining test isolation and preventing state from one test from affecting another.

The ``picodi_override`` Marker
==============================
Instead of using ``with registry.override(...):`` inside your test functions, the `pytest` plugin provides a more convenient
``@pytest.mark.picodi_override`` marker.

.. code-block:: python

    # test_pytest_integration.py
    import pytest
    from picodi import registry, Provide, inject

    # Assume production code from previous examples:
    # get_live_api_client, process_data_from_api


    # --- Production Code (Simplified) ---
    def get_live_api_client():
        print("PROD: Creating live API client")
        return "RealApiClient"


    @inject
    def process_data_from_api(client=Provide(get_live_api_client)):
        print(f"SERVICE: Processing using {client}")
        return f"Data processed by {client}"


    # --- Test Code ---
    def get_mock_api_client():
        print("TEST: Creating mock API client")
        return "MockApiClient"


    # Use the marker to override get_live_api_client with get_mock_api_client
    @pytest.mark.picodi_override(get_live_api_client, get_mock_api_client)
    def test_with_picodi_marker():
        print("\nTEST_MARKER: Starting test")
        result = process_data_from_api()
        assert result == "Data processed by MockApiClient"
        print("TEST_MARKER: Test finished")


    # To run: pytest test_pytest_integration.py -s

The marker applies the override for the duration of the test function, and the plugin ensures it's cleaned up afterward.

Overriding Multiple Dependencies
================================
You can override multiple dependencies by providing a list of tuples to the marker:

.. code-block:: python

    def get_original_dep_1(): ...
    def get_mock_dep_1(): ...
    def get_original_dep_2(): ...
    def get_mock_dep_2(): ...


    @pytest.mark.picodi_override(
        [
            (get_original_dep_1, get_mock_dep_1),
            (get_original_dep_2, get_mock_dep_2),
        ]
    )
    def test_with_multiple_overrides():
        pass

Testing Asynchronous Code
=========================
If your tests involve asynchronous code and you use ``async def`` test functions (often with a library like `pytest-asyncio`),
you should also include the ``picodi.integrations._pytest_asyncio`` plugin in your ``conftest.py``, as shown in the setup
section. This ensures that Picodi's overrides and cleanup integrate correctly with the asyncio event loop used by your tests.

The usage of ``@pytest.mark.picodi_override`` remains the same for async test functions.

.. code-block:: python

    import pytest
    from picodi import Provide, inject


    async def get_async_live_service():
        print("PROD_ASYNC: Live service")
        return "AsyncLiveService"


    async def get_async_mock_service():
        print("TEST_ASYNC: Mock service")
        return "AsyncMockService"


    @inject
    async def use_async_service(service=Provide(get_async_live_service)):
        return f"Used {service}"


    @pytest.mark.picodi_override(get_async_live_service, get_async_mock_service)
    @pytest.mark.asyncio
    async def test_async_service_with_override():
        result = await use_async_service()
        assert result == "Used AsyncMockService"

*************
Key Takeaways
*************

*   Use ``registry.override()`` as a context manager for manual, temporary overrides.
*   For ``pytest`` projects, enable the ``picodi.integrations._pytest`` plugin in ``conftest.py``.
*   Use the ``@pytest.mark.picodi_override`` marker for cleaner test-specific overrides.
*   The plugin handles automatic cleanup of overrides and manual-scoped dependencies after each test.
*   For async tests, also include ``picodi.integrations._pytest_asyncio`` if needed.
*   Effective use of overrides is key to writing isolated and maintainable tests for DI-managed code.

Next, let's look at :ref:`Framework Integration <topics_integrations>`.
