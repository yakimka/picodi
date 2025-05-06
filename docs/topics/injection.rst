.. _topics_injection:

####################
Dependency Injection
####################

Once you have defined your :ref:`dependency providers <topics_dependencies>`,
you need a way to supply their results to the functions or methods that require them.
This process is called **injection**, and Picodi handles it using the :func:`~picodi.inject`
decorator and the :func:`~picodi.Provide` marker.

*************************
The ``@inject`` Decorator
*************************

The ``@inject`` decorator is the core mechanism that enables dependency injection
for a specific function or method.

.. testcode:: inject_decorator

    from picodi import inject, Provide


    def get_dependency():
        return "some_value"


    @inject  # Enable dependency injection for this function
    def my_function(param=Provide(get_dependency)):
        # ... function body ...
        print(f"Injected value: {param}")


    my_function()

**Output:**

.. testoutput:: inject_decorator

    Injected value: some_value

**How it works:**

*   ``@inject`` wraps the decorated function (``my_function`` in this case).
*   When the wrapped function is called, ``@inject``
    intercepts the call *before* the original function's code executes.
*   It inspects the function's signature for parameters whose default values are ``Provide()`` markers.
*   For each such parameter, it resolves the specified dependency provider (e.g., calls ``get_dependency``).
*   It manages the lifecycle of the resolved dependency based on its :ref:`scope <topics_scopes>`.
*   Finally, it calls the original function, passing the resolved dependencies as
    arguments for the corresponding parameters (unless arguments were explicitly passed during the call).

**Placement:**

The ``@inject`` decorator should generally be the **first decorator** applied to your function
(i.e., the one closest to the ``def`` keyword). This ensures it can correctly analyze
the function signature before other decorators potentially modify it.

.. code-block:: python

    # Correct placement
    @other_decorator
    @inject
    def my_func(val=Provide(...)): ...


    # Incorrect placement (might work, but not guaranteed)
    @inject
    @other_decorator
    def my_func(val=Provide(...)): ...

**********************************
The ``Provide`` Marker
**********************************

:func:`~picodi.Provide` is used as a **default value** for a function parameter to signal
to ``@inject`` that this parameter should be filled by a dependency.

.. testcode:: provide_marker

    from picodi import Provide, inject


    def get_user_name() -> str:
        return "Alice"


    def get_user_id() -> int:
        return 123


    @inject
    def process_user(
        user_id: int = Provide(get_user_id),  # Inject user_id
        name: str = Provide(get_user_name),  # Inject name
    ):
        print(f"Processing user {name} (ID: {user_id})")


    process_user()

**Output:**

.. testoutput:: provide_marker

    Processing user Alice (ID: 123)

**Key Points:**

*   ``Provide()`` takes exactly one argument: the **dependency provider callable**
    (e.g., ``get_user_id``). Do *not* call the provider function inside
    ``Provide`` (e.g., ``Provide(get_user_id())`` is incorrect).
*   It acts as a placeholder default value. If you explicitly pass an argument for a
    parameter marked with ``Provide`` when calling the function, your explicitly passed
    value will be used instead of the injected dependency.

    .. testcode:: provide_marker

        # Explicitly passing user_id overrides injection for that parameter
        process_user(user_id=999)

    **Output:**

    .. testoutput:: provide_marker

        Processing user Alice (ID: 999)

*   Type hints (``user_id: int``, ``name: str``) are strongly recommended for clarity
    and static analysis but are not required by Picodi for injection itself.
    Picodi relies on the ``Provide()`` marker, not type hints.

***************************
Dependency Resolution Graph
***************************

Picodi automatically handles cases where dependencies depend on other dependencies.
It builds a dependency graph and resolves it in the correct order.

.. code-block:: python

    from picodi import Provide, inject


    def get_config() -> dict:
        print("Resolving: get_config")
        return {"db_url": "sqlite:///:memory:"}


    @inject  # Depends on get_config
    def get_db_connection(config: dict = Provide(get_config)) -> str:
        print("Resolving: get_db_connection")
        return f"Connection({config['db_url']})"


    @inject  # Depends on get_db_connection
    def get_user_repo(conn: str = Provide(get_db_connection)) -> str:
        print("Resolving: get_user_repo")
        return f"UserRepo({conn})"


    @inject  # Depends on get_user_repo
    def main_service(repo: str = Provide(get_user_repo)):
        print(f"Running main_service with {repo}")


    main_service()

**Output:**

.. testoutput:: dependency_graph

    Resolving: get_config
    Resolving: get_db_connection
    Resolving: get_user_repo
    Running main_service with UserRepo(Connection(sqlite:///:memory:))

Picodi resolved the chain: ``get_config`` -> ``get_db_connection`` -> ``get_user_repo`` -> ``main_service``.

**********************
Injecting into Methods
**********************

You can use ``@inject`` on methods, including ``__init__``, just like regular functions.

.. code-block:: python

    from picodi import Provide, inject


    def get_logger():
        print("Creating logger")
        return "MyLogger"


    class MyService:
        @inject
        def __init__(self, logger=Provide(get_logger)):
            print("MyService.__init__ called")
            self.logger = logger

        def do_something(self):
            print(f"Doing something with {self.logger}")


    service = MyService()
    service.do_something()

**Output:**

.. code-block:: text

    Creating logger
    MyService.__init__ called
    Doing something with MyLogger

************************
Sync vs. Async Injection
************************

*   A **synchronous** function (``def``) can only inject **synchronous** dependencies.
    Attempting to ``Provide`` an ``async def`` dependency in a synchronous function will
    result in the coroutine object being injected, not its result.
    (Exception: See the :ref:`section <topics_async_in_sync>` on injecting async dependencies
    into sync functions in :doc:`/topics/async` for manually initialized async dependencies).
*   An **asynchronous** function (``async def``) can inject
    **both synchronous and asynchronous** dependencies. Picodi will correctly ``await``
    async dependencies when resolving them within an async function.

*************
Key Takeaways
*************

*   Use ``@inject`` (placed first) to enable dependency injection for a function/method.
*   Use ``Provide(dependency_provider)`` as the default value for parameters that need injection.
*   Picodi resolves the full dependency graph automatically.
*   Injection works for regular functions and methods (like ``__init__``).
*   Sync functions generally require sync dependencies; async functions can handle both.

Next, let's dive deeper into controlling the lifecycle of
these injected dependencies using :ref:`Scopes <topics_scopes>`.
