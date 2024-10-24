Overriding Dependencies
=======================

You can override dependencies at runtime. This is important for testing and useful
for implementing "abstract" dependencies.

.. testcode::

    import pytest

    from picodi import registry


    # Dependency that return app settings
    #   usually it should be implemented in the app
    def get_settings():
        pass


    def get_test_settings():
        return {"test": "settings"}


    @pytest.fixture()
    def _settings():
        with registry.override(get_settings, get_test_settings):
            # use yield, so the override will be cleared after each test
            yield

You can also use :func:`picodi.registry.override` as a regular method call.

.. testcode::

    from picodi import registry


    def get_settings() -> dict:
        pass


    def get_test_setting():
        return {"test": "settings"}


    registry.override(get_settings, get_test_setting)

Abstract Dependencies
---------------------

"Abstract" dependencies can be used to provide a default implementation for a dependency,
which can be overridden at runtime. This is useful for reusing dependencies in different contexts.

.. testcode::

    from picodi import Provide, inject, registry


    def get_abc_setting() -> dict:
        raise NotImplementedError


    @inject
    def my_service(settings: dict = Provide(get_abc_setting)) -> dict:
        return settings


    @registry.override(get_abc_setting)
    def get_setting():
        return {"my": "settings"}


    print(my_service())
    # Output: {'my': 'settings'}

.. testoutput::

    {'my': 'settings'}

Clearing Overrides
------------------

To clear a specific override, you can pass None as the new dependency.

.. testcode::

    from picodi import registry


    registry.override(get_abc_setting, None)

To clear all overrides, you can use :func:`picodi.registry.clear_overrides`.

.. testcode::

    from picodi import registry


    registry.clear_overrides()
