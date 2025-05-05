.. _tutorial_dependency_overrides:

###################################
Tutorial: 05 - Dependency Overrides
###################################

One of the key benefits of Dependency Injection is the ability to easily swap implementations. Picodi provides a mechanism to **override** a dependency, replacing its provider function with a different one at runtime.

**************************
Why Override Dependencies?
**************************

Common use cases for overriding include:

*   **Testing:** Replacing real dependencies (like database connections or external API clients) with mock objects or simplified test doubles.
*   **Configuration:** Using different dependency implementations based on the environment (e.g., a fake email sender in development vs. a real one in production).
*   **Feature Flags:** Swapping implementations based on feature flags.

********************************
Using ``registry.override``
********************************

The primary tool for this is ``picodi.registry.override()``. It can be used as a context manager or a decorator.

**Override as a Context Manager**

Using ``registry.override`` as a context manager is ideal for temporarily replacing a dependency, often within tests or specific code blocks. The override is automatically removed when the ``with`` block exits.

Let's reuse our first example and override the `get_api_base_url` dependency to point to a staging server instead of the production one.

.. testcode:: overrides_context

    # dependencies.py
    def get_api_base_url() -> str:
        """Provides the base URL for the PRODUCTION API."""
        print("Original Dep: Providing PRODUCTION URL")
        return "https://api.example.com"


    def get_staging_api_base_url() -> str:
        """Provides the base URL for the STAGING API."""
        print("Override Dep: Providing STAGING URL")
        return "https://api.staging.example.com"


    # services.py
    from picodi import Provide, inject
    from dependencies import get_api_base_url


    @inject
    def call_external_api(
        endpoint: str,
        base_url: str = Provide(get_api_base_url),  # Depends on get_api_base_url
    ) -> str:
        """Calls an endpoint on the external API."""
        full_url = f"{base_url}/{endpoint.lstrip('/')}"
        print(f"Service: Calling API at: {full_url}")
        return f"Response from {full_url}"


    # main.py
    from picodi import registry  # Need registry for override
    from services import call_external_api
    from dependencies import get_api_base_url, get_staging_api_base_url

    print("--- Calling without override ---")
    response_prod = call_external_api("users")
    print(f"Response: {response_prod}\n")

    print("--- Calling within override context ---")
    # Use override as a context manager
    with registry.override(get_api_base_url, get_staging_api_base_url):
        response_staging = call_external_api("users")
        print(f"Response: {response_staging}")
    print("--- Exited override context ---\n")

    print("--- Calling again without override ---")
    response_prod_again = call_external_api("users")
    print(f"Response: {response_prod_again}")

**Explanation:**

1.  **``registry.override(original, override)``:** We call ``registry.override``, passing the original dependency function (``get_api_base_url``) and the function we want to use instead (``get_staging_api_base_url``).
2.  **Context:** Inside the ``with`` block, any injection requesting ``get_api_base_url`` will actually receive the result from ``get_staging_api_base_url``.
3.  **Reversion:** Once the ``with`` block exits, the override is automatically removed, and subsequent calls use the original ``get_api_base_url`` again.

**Output:**

.. testoutput:: overrides_context

    --- Calling without override ---
    Original Dep: Providing PRODUCTION URL
    Service: Calling API at: https://api.example.com/users
    Response: Response from https://api.example.com/users

    --- Calling within override context ---
    Override Dep: Providing STAGING URL
    Service: Calling API at: https://api.staging.example.com/users
    Response: Response from https://api.staging.example.com/users
    --- Exited override context ---

    --- Calling again without override ---
    Original Dep: Providing PRODUCTION URL
    Service: Calling API at: https://api.example.com/users
    Response: Response from https://api.example.com/users

**Override as a Decorator**

You can also use ``@registry.override(original)`` to decorate the overriding function. This permanently registers the override (until cleared). This is less common than the context manager but can be useful for setting up test environments globally.

.. testcode:: overrides_decorator

    # (dependencies.py and services.py are the same as above)
    # dependencies.py
    def get_api_base_url() -> str:
        """Provides the base URL for the PRODUCTION API."""
        print("Original Dep: Providing PRODUCTION URL")
        return "https://api.example.com"


    # services.py
    from picodi import Provide, inject
    from dependencies import get_api_base_url


    @inject
    def call_external_api(
        endpoint: str,
        base_url: str = Provide(get_api_base_url),  # Depends on get_api_base_url
    ) -> str:
        """Calls an endpoint on the external API."""
        full_url = f"{base_url}/{endpoint.lstrip('/')}"
        print(f"Service: Calling API at: {full_url}")
        return f"Response from {full_url}"


    # main_decorator.py
    from picodi import registry
    from services import call_external_api
    from dependencies import get_api_base_url


    # Use override as a decorator
    @registry.override(get_api_base_url)
    def get_decorated_staging_url() -> str:
        """Provides the base URL for the STAGING API via decorator."""
        print("Decorated Override Dep: Providing STAGING URL")
        return "https://decorator.staging.example.com"


    print("--- Calling with decorator override active ---")
    response_staging = call_external_api("products")
    print(f"Response: {response_staging}\n")

    # Overrides persist until cleared
    print("--- Calling again, override still active ---")
    response_staging_again = call_external_api("orders")
    print(f"Response: {response_staging_again}\n")

    # Clear the override manually
    print("--- Clearing the specific override ---")
    registry.override(get_api_base_url, None)  # Pass None to clear

    print("--- Calling after clearing override ---")
    response_prod = call_external_api("users")
    print(f"Response: {response_prod}")

    # You can also clear ALL overrides at once
    # registry.clear_overrides()

**Output:**

.. testoutput:: overrides_decorator

    --- Calling with decorator override active ---
    Decorated Override Dep: Providing STAGING URL
    Service: Calling API at: https://decorator.staging.example.com/products
    Response: Response from https://decorator.staging.example.com/products

    --- Calling again, override still active ---
    Decorated Override Dep: Providing STAGING URL
    Service: Calling API at: https://decorator.staging.example.com/orders
    Response: Response from https://decorator.staging.example.com/orders

    --- Clearing the specific override ---
    --- Calling after clearing override ---
    Original Dep: Providing PRODUCTION URL
    Service: Calling API at: https://api.example.com/users
    Response: Response from https://api.example.com/users


********************
Clearing Overrides
********************

*   To clear a *specific* override, call ``registry.override(original_dependency, None)``.
*   To clear *all* active overrides, call ``registry.clear_overrides()``.

This is crucial in testing frameworks to ensure overrides from one test don't leak into others.

***********
Next Steps
***********

Overrides are essential for testing. Let's dive deeper into how Picodi integrates with testing workflows, particularly with ``pytest``: :ref:`Testing <tutorial_testing>`.
