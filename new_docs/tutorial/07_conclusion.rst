.. _tutorial_conclusion:

#########################
Tutorial: 07 - Conclusion
#########################

Congratulations! You've completed the Picodi tutorial.

*******************
What You've Learned
*******************

Through these steps, you've gained a practical understanding of Picodi's core features:

*   **Defining Dependencies:** How simple Python functions (sync and async) act as
    dependency providers. (:ref:`Step 1 <tutorial_first_steps>`)
*   **Injection:** Using :func:`~picodi.inject` and :func:`~picodi.Provide`
    to automatically supply dependencies to functions. (:ref:`Step 1 <tutorial_first_steps>`)
*   **Yield Dependencies:** Managing dependency setup and teardown using ``yield``
    for resources requiring cleanup.
    (:ref:`Step 2 <tutorial_yield_dependencies>`, :ref:`Step 4 <tutorial_async_dependencies>`)
*   **Scopes:** Controlling dependency instance lifecycle and caching using
    :class:`~picodi.NullScope` and :class:`~picodi.SingletonScope`. (:ref:`Step 3 <tutorial_scopes>`)
*   **Async Support:** Defining and injecting asynchronous dependencies seamlessly.
    (:ref:`Step 4 <tutorial_async_dependencies>`)
*   **Overrides:** Replacing dependency implementations at runtime using
    :func:`picodi.Registry.override`, crucial for testing and configuration.
    (:ref:`Step 5 <tutorial_dependency_overrides>`)
*   **Testing:** Leveraging overrides and the ``pytest`` plugin for effective testing.
    (:ref:`Step 6 <tutorial_testing>`)

****************
Where to Go Next
****************

This tutorial covered the fundamentals. To deepen your understanding and explore more
advanced features, check out the **User Guide**:

*   :doc:`/topics/dependencies`: More details on defining dependencies.
*   :doc:`/topics/injection`: In-depth look at the ``@inject`` decorator.
*   :doc:`/topics/scopes`: Explore all built-in scopes
    (``NullScope``, ``SingletonScope``, ``ContextVarScope``) and how to create custom ones.
*   :doc:`/topics/overriding`: Advanced override techniques.
*   :doc:`/topics/lifespan`: Using :func:`picodi.Registry.lifespan`` and
    :func:`picodi.Registry.alifespan` for managing application lifecycle.
*   :doc:`/topics/async`: Specific considerations for async applications.
*   :doc:`/topics/testing`: Comprehensive guide to testing with Picodi.
*   :doc:`/topics/integrations`: How to use Picodi with frameworks like FastAPI and Starlette.
*   :doc:`/topics/best_practices`: Recommendations for using Picodi effectively.

You can also consult the :doc:`/api/picodi` for detailed information on specific functions and classes.

We hope this tutorial has provided a solid foundation for using Picodi in your projects. Happy coding!
