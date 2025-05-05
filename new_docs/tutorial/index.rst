.. _tutorial:

########
Tutorial
########

This tutorial provides a hands-on introduction to Picodi.
We'll build a simple application step-by-step, demonstrating the core features of the library.

By the end of this tutorial, you will understand:

*   How to define basic dependencies.
*   How to inject dependencies into your functions using :func:`picodi.inject` and :func:`picodi.Provide`.
*   How to work with dependencies that require setup and teardown (yield dependencies).
*   How to use different scopes to manage dependency lifecycles.
*   How to handle asynchronous dependencies.
*   How to override dependencies for testing or different configurations.

Let's get started!

.. toctree::
   :maxdepth: 1

   01_first_steps
   02_yield_dependencies
   03_scopes
   04_async_dependencies
   05_dependency_overrides
   06_testing
   07_conclusion

**Prerequisites:**

*   Python 3.10 or higher.
*   Picodi installed (``pip install picodi``).
