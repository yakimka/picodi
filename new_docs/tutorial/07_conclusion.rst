.. _tutorial_conclusion:

########################
Tutorial: 07 - Conclusion
########################

Congratulations! You've completed the Picodi tutorial.

*****************
What You've Learned
*****************

Through these steps, you've gained a practical understanding of Picodi's core features:

*   **Defining Dependencies:** How simple Python functions (sync and async) act as dependency providers. (:ref:`Step 1 <tutorial_first_steps>`)
*   **Injection:** Using `@inject` and `Provide` to automatically supply dependencies to functions. (:ref:`Step 1 <tutorial_first_steps>`)
*   **Yield Dependencies:** Managing dependency setup and teardown using `yield` for resources requiring cleanup. (:ref:`Step 2 <tutorial_yield_dependencies>`, :ref:`Step 4 <tutorial_async_dependencies>`)
*   **Scopes:** Controlling dependency instance lifecycle and caching using `NullScope` and `SingletonScope`. (:ref:`Step 3 <tutorial_scopes>`)
*   **Async Support:** Defining and injecting asynchronous dependencies seamlessly. (:ref:`Step 4 <tutorial_async_dependencies>`)
*   **Overrides:** Replacing dependency implementations at runtime using `registry.override`, crucial for testing and configuration. (:ref:`Step 5 <tutorial_dependency_overrides>`)
*   **Testing:** Leveraging overrides and the `pytest` plugin for effective testing. (:ref:`Step 6 <tutorial_testing>`)

*****************
Where to Go Next
*****************

This tutorial covered the fundamentals. To deepen your understanding and explore more advanced features, check out the **User Guide**:

*   :ref:`topics_dependencies`: More details on defining dependencies.
*   :ref:`topics_injection`: In-depth look at the `@inject` decorator.
*   :ref:`topics_scopes`: Explore all built-in scopes (`NullScope`, `SingletonScope`, `ContextVarScope`) and how to create custom ones.
*   :ref:`topics_overriding`: Advanced override techniques.
*   :ref:`topics_lifespan`: Using `registry.lifespan` and `registry.alifespan` for managing application lifecycle.
*   :ref:`topics_async`: Specific considerations for async applications.
*   :ref:`topics_testing`: Comprehensive guide to testing with Picodi.
*   :ref:`topics_integrations`: How to use Picodi with frameworks like FastAPI and Starlette.
*   :ref:`topics_best_practices`: Recommendations for using Picodi effectively.

You can also consult the :ref:`api_reference` for detailed information on specific functions and classes.

We hope this tutorial has provided a solid foundation for using Picodi in your projects. Happy coding!
