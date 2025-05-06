.. _tutorial_first_steps:

##########################
Tutorial: 01 - First Steps
##########################

Let's start with the basics: defining a dependency and injecting it into a function that needs it.

*********************
Defining a Dependency
*********************

In Picodi, a dependency is simply a Python function (or any callable) that returns a value.
This function typically has no required arguments.

Let's define a dependency that provides a simple configuration setting:

.. testcode:: first_steps

    # dependencies.py
    def get_api_base_url() -> str:
        """Provides the base URL for an external API."""
        print("Creating API base URL dependency")
        return "https://api.example.com"

This is a standard Python function. Picodi doesn't require any special base classes or
decorators *just* to define a dependency.

**************************
Injecting the Dependency
**************************

Now, let's create a function that needs this API base URL to perform its task.
We'll use Picodi's :func:`~picodi.inject` decorator and :func:`~picodi.Provide` marker
to tell Picodi how to supply the dependency.

.. testcode:: first_steps

    # services.py
    from picodi import Provide, inject

    # Assume dependencies.py is in the same directory or Python path
    # from dependencies import get_api_base_url


    @inject
    def call_external_api(
        endpoint: str, base_url: str = Provide(get_api_base_url)  # Inject here!
    ) -> str:
        """Calls an endpoint on the external API."""
        full_url = f"{base_url}/{endpoint.lstrip('/')}"
        print(f"Calling API at: {full_url}")
        # In a real app, you'd use an HTTP client here
        return f"Response from {full_url}"

**Explanation:**

1.  **@inject:** This decorator modifies ``call_external_api`` so that Picodi can manage its
    dependencies before the function's actual code runs.
    It should generally be the *first* decorator applied (closest to the ``def``).
2.  **Provide(get_api_base_url):** This is used as the *default value* for the ``base_url`` parameter.
    It tells ``@inject``: "When ``call_external_api`` is called, if no value is explicitly passed
    for ``base_url``, call the ``get_api_base_url`` function and use its return value for this parameter."

***************************
Using the Injected Function
***************************

Now you can call `call_external_api` like a regular function. Picodi handles the injection automatically.

.. testcode:: first_steps

    # main.py
    # from services import call_external_api

    response = call_external_api("users")
    print(response)

    response_2 = call_external_api("products")
    print(response_2)

**Output:**

.. testoutput:: first_steps

    Creating API base URL dependency
    Calling API at: https://api.example.com/users
    Response from https://api.example.com/users
    Creating API base URL dependency
    Calling API at: https://api.example.com/products
    Response from https://api.example.com/products

Notice that ``get_api_base_url`` was called each time ``call_external_api`` was invoked.
This is the default behavior (using :class:`~picodi.NullScope`).
We'll explore how to change this later using :ref:`scopes <tutorial_scopes>`.

*********************************
Dependencies Depending on Others
*********************************

Dependencies can also depend on other dependencies. Picodi automatically resolves the entire chain.

Let's define a configuration dependency and have our URL dependency use it:

.. testcode:: first_steps_nested

    # dependencies.py
    from picodi import Provide, inject


    def get_config() -> dict:
        """Provides application configuration."""
        print("Loading config")
        return {"api_url": "https://api.config.com"}


    @inject  # Inject config here
    def get_api_base_url(config: dict = Provide(get_config)) -> str:
        """Provides the base URL from config."""
        print("Creating API base URL from config")
        return config["api_url"]


    # services.py
    # (call_external_api remains the same, using get_api_base_url)
    # from dependencies import get_api_base_url
    from picodi import Provide, inject


    @inject
    def call_external_api(endpoint: str, base_url: str = Provide(get_api_base_url)) -> str:
        """Calls an endpoint on the external API."""
        full_url = f"{base_url}/{endpoint.lstrip('/')}"
        print(f"Calling API at: {full_url}")
        return f"Response from {full_url}"


    # main.py
    # from services import call_external_api

    response = call_external_api("orders")
    print(response)

**Output:**

.. testoutput:: first_steps_nested

    Loading config
    Creating API base URL from config
    Calling API at: https://api.config.com/orders
    Response from https://api.config.com/orders

Picodi first called ``get_config``, then injected its result into ``get_api_base_url``
when resolving the dependencies for ``call_external_api``, and finally injected the
result of ``get_api_base_url`` into the ``call_external_api`` execution.

***********
Next Steps
***********

You've learned the basics of defining and injecting simple dependencies.
Next, we'll look at dependencies that need cleanup after they are used:
:ref:`Yield Dependencies <tutorial_yield_dependencies>`.
