.. _picodi_documentation:

####################
Picodi Documentation
####################

**Picodi** is a straightforward and powerful Dependency Injection (DI) library for Python, designed to simplify managing dependencies in both synchronous and asynchronous applications.

`Dependency Injection <https://en.wikipedia.org/wiki/Dependency_injection>`_ is a design pattern where an object receives its dependencies from an external source rather than creating them itself. Picodi helps you implement this pattern effectively, making your code more modular, testable, and maintainable.

Inspired by FastAPI's DI system but usable in any Python project (framework-agnostic), Picodi offers:

*   **Simplicity:** Easy-to-understand API.
*   **Flexibility:** Works seamlessly in sync and async code.
*   **Zero Dependencies:** Lightweight and requires only Python.
*   **Lifecycle Management:** Control over dependency creation and cleanup using scopes and lifespans.
*   **Testability:** Built-in support for overriding dependencies in tests.
*   **Type Hint Friendly:** Integrates well with Python's type system.

Whether you're building a web application with FastAPI, a CLI tool, or any other Python project, Picodi can help you manage your dependencies cleanly.

*************
Documentation
*************

.. toctree::
   :maxdepth: 2
   :caption: Getting Started

   introduction/index
   tutorial/index

.. toctree::
   :maxdepth: 2
   :caption: User Guide

   topics/dependencies
   topics/injection
   topics/scopes
   topics/overriding
   topics/lifespan
   topics/async
   topics/testing
   topics/integrations
   topics/best_practices

.. toctree::
   :maxdepth: 2
   :caption: Help & Info

   faq

.. toctree::
    :hidden:
    :caption: Indices and tables

    genindex
    api/picodi

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

****************
Project Links
****************

*   `GitHub <https://github.com/yakimka/picodi>`_
*   `PyPI <https://pypi.org/project/picodi>`_
*   `FastAPI Example Project <https://github.com/yakimka/picodi-fastapi-example>`_
