.. _topics_testing:

######################
Testing with Picodi
######################

One of the primary motivations for using Dependency Injection is to improve the **testability** of your code. Picodi makes it easy to replace real dependencies with mocks, stubs, or test doubles during testing, allowing you to write isolated and reliable unit tests.

********************************
The Role of Dependency Overrides
********************************

The core feature enabling testing is :ref:`dependency overriding <topics_overriding>`. By overriding a dependency provider (like one that connects to a real database or external API), you can substitute it with a controlled, predictable alternative within your tests.

********************************
Manual Overrides in Tests
********************************

You can directly use `registry.override` as a context manager within your test functions. This is useful for simple cases or when not using a testing framework with specific Picodi integration.

.. code-block:: python

    # test_example.py
    import pytest
    from picodi import registry, Provide, inject

    # --- Production Code ---
    def get_live_api_client():
        print("PROD: Creating live API client")
        # ... returns a real client ...
        return "RealApiClient"

    @inject
    def process_data_from_api(client = Provide(get_live_api_client)):
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

Remember to manage cleanup if your overrides involve dependencies with manual scopes, although using the context manager handles clearing the override itself.

********************************
Pytest Integration
********************************

Picodi provides a dedicated `pytest` plugin that significantly simplifies testing workflows by automating setup and cleanup.

Setup
