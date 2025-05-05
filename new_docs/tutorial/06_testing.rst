.. _tutorial_testing:

######################
Tutorial: 06 - Testing
######################

Dependency Injection significantly improves the testability of your code. By injecting dependencies, you can easily replace real implementations with mocks or test doubles during your tests. Picodi provides features to make this process straightforward, especially when using frameworks like ``pytest``.

********************************
Testing with Manual Overrides
********************************

The core mechanism for testing is ``registry.override``, which we saw in the :ref:`previous step <tutorial_dependency_overrides>`. You can use it directly within your test functions as a context manager.

Let's write a test for our ``call_external_api`` service. We want to ensure it constructs the correct URL without actually making a network call. We'll override ``get_api_base_url`` to provide a known test URL.

.. code-block:: python

    # test_services.py
    import pytest
    from picodi import registry
    # Assume services.py and dependencies.py are importable
    from services import call_external_api
    from dependencies import get_api_base_url

    def get_test_api_url() -> str:
        """A dependency providing a fixed URL for testing."""
        print("Test Override: Providing TEST URL")
        return "http://test.server.com"

    def test_call_external_api_constructs_correct_url():
        """Verify the service constructs the URL correctly using an override."""
        endpoint = "test/endpoint"
        expected_url = f"http://test.server.com/{endpoint}"

        print("\nTest: Setting up override context...")
        with registry.override(get_api_base_url, get_test_api_url):
            print("Test: Calling service inside override context.")
            response = call_external_api(endpoint)
            print("Test: Service call returned.")

            # Check if the service function behaved as expected
            # (In a real test, you might check logs or mock calls)
            assert f"Response from {expected_url}" == response
        print("Test: Exited override context.")

    # To run this test: pytest test_services.py -s
    # The -s flag shows print statements

Running this test with ``pytest -s`` would show:

.. code-block:: text

    Test: Setting up override context...
    Test Override: Providing TEST URL
    Test: Calling service inside override context.
    Service: Calling API at: http://test.server.com/test/endpoint
    Test: Service call returned.
    Test: Exited override context.
    .                                    [100%]

The test passes, and we can see that our ``get_test_api_url`` was correctly used instead of the original ``get_api_base_url``. The override was automatically cleaned up after the ``with`` block.

********************************
Pytest Integration
********************************

While manual overrides work, managing them across many tests can be cumbersome. Picodi offers a built-in ``pytest`` plugin to simplify this.

**Setup:**

Add the plugin to your root ``conftest.py``:

.. code-block:: python

    # conftest.py
    pytest_plugins = [
        "picodi.integrations._pytest",
        # If using async tests with pytest-asyncio, add this *after* the main plugin:
        # "picodi.integrations._pytest_asyncio",
    ]

**Automatic Cleanup:**

The plugin automatically handles cleanup after each test:

*   Calls ``registry.shutdown()`` to clean up scoped dependencies (like Singletons).
*   Calls ``registry.clear_overrides()`` to remove any overrides set during the test.
*   Calls ``registry.clear_touched()`` (more on this in advanced topics).

This ensures tests are isolated from each other.

**``picodi_override`` Marker:**

Instead of using the ``with registry.override(...)`` context manager, you can use the ``@pytest.mark.picodi_override`` marker directly on your test function.

Let's rewrite the previous test using the marker:

.. code-block:: python

    # test_services_pytest.py
    import pytest
    from picodi import registry # No longer needed for override context
    from services import call_external_api
    from dependencies import get_api_base_url

    def get_test_api_url() -> str:
        """A dependency providing a fixed URL for testing."""
        print("Test Override: Providing TEST URL")
        return "http://test.server.com"

    # Apply the override using the marker
    @pytest.mark.picodi_override(get_api_base_url, get_test_api_url)
    def test_call_external_api_with_marker(): # No pytester fixture needed here
        """Verify the service constructs the URL correctly using the marker."""
        endpoint = "test/endpoint"
        expected_url = f"http://test.server.com/{endpoint}"

        print("\nTest: Calling service with marker override active.")
        response = call_external_api(endpoint)
        print("Test: Service call returned.")

        assert f"Response from {expected_url}" == response
        print("Test: Test function finished.")
        # Cleanup happens automatically after this test runs

    # To run: pytest test_services_pytest.py -s

The output with ``pytest -s`` will be similar, showing the test override being used:

.. code-block:: text

    Test: Calling service with marker override active.
    Test Override: Providing TEST URL
    Service: Calling API at: http://test.server.com/test/endpoint
    Test: Service call returned.
    Test: Test function finished.
    .                                     [100%]

The marker approach is cleaner and less verbose for applying overrides in tests. You can also override multiple dependencies by passing a list of tuples to the marker: ``@pytest.mark.picodi_override([(dep1, override1), (dep2, override2)])``.

***********
Next Steps
***********

You've completed the core Picodi tutorial! You now have the foundational knowledge to use Picodi for managing dependencies in your projects. Proceed to the :ref:`Conclusion <tutorial_conclusion>` for a summary and pointers to further topics.
