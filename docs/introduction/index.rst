.. _introduction:

############
Introduction
############

Welcome to Picodi! This guide will introduce you to the core concepts of Dependency Injection (DI)
and how Picodi helps you apply them in your Python projects.

*****************************
What is Dependency Injection?
*****************************

Dependency Injection is a design pattern used to achieve Inversion of Control (IoC)
between components and their dependencies.
Instead of an object creating its own dependencies (the objects it needs to function),
these dependencies are "injected" from an external source.

**Why use DI?**

*   **Decoupling:** Objects don't need to know how to create their dependencies.
    This reduces coupling between components, making the system more modular.
*   **Testability:** Dependencies can be easily replaced with mock objects during testing,
    allowing for isolated tests.
*   **Flexibility & Maintainability:** It's easier to change or configure dependencies without
    modifying the objects that use them. Code becomes cleaner and easier to manage.

**Example without DI:**

.. code-block:: python

    class DatabaseConnection:
        def __init__(self, connection_string: str):
            self._connection = connect(connection_string)  # Assume connect exists

        def fetch_data(self, query: str):
            # ... fetch data using self._connection
            pass


    class UserService:
        def __init__(self):
            # UserService creates its own dependency
            self.db_connection = DatabaseConnection("my_db_string")

        def get_user(self, user_id: int):
            # ... uses self.db_connection
            pass

In this example, ``UserService`` is tightly coupled to ``DatabaseConnection``.
Testing ``UserService`` without a real database connection is difficult.

**Example with DI:**

.. code-block:: python

    class DatabaseConnection:
        # ... (same as before)
        pass


    class UserService:
        def __init__(self, db_connection: DatabaseConnection):
            # Dependency is passed in (injected)
            self.db_connection = db_connection

        def get_user(self, user_id: int):
            # ... uses self.db_connection
            pass


    # Somewhere else in the application (e.g., the entry point)
    db_conn = DatabaseConnection("my_db_string")
    user_service = UserService(db_conn)  # Injection happens here

Now, ``UserService`` receives its ``DatabaseConnection`` dependency.
We can easily provide a different ``DatabaseConnection`` (e.g., a mock for testing) without changing ``UserService``.

****************
How Picodi Helps
****************

Picodi provides a simple and elegant way to manage this injection process.
It acts as a mechanism (**injection**) to automatically provide **dependencies** (using simple functions)
to the functions or classes that need them.

Key concepts in Picodi:

*   **Dependency Function:** A regular Python function (sync or async) that knows how to create an instance of a dependency.
    It might return a value directly or yield it (for dependencies needing cleanup).
*   **Decorator** :func:`~picodi.inject` **:** Marks a function or method as requiring dependency injection.
*   **Marker:** :func:`~picodi.Provide` **:** Used within the signature of an ``@inject``-ed function to specify which
    dependency function should provide the value for a parameter.
*   **Registry** :attr:`~picodi.registry` **:** The central object managing dependencies, their scopes, and overrides.

Picodi handles resolving the dependency graph (dependencies that depend on other dependencies) and
manages their lifecycle (creation and cleanup) based on defined :doc:`/topics/scopes`.

Ready to see it in action? Head over to the :ref:`tutorial`!
