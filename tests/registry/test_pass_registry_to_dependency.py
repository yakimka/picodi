from __future__ import annotations

from picodi import Provide, Registry, inject
from picodi import registry as picodi_registry


def test_can_pass_registry_to_dependency():
    def get_dep(registry):
        return registry

    @inject
    def service(dep=Provide(get_dep)):
        return dep

    result = service()

    assert result is picodi_registry


async def test_can_pass_registry_to_dependency_async():
    async def get_dep(registry):
        return registry

    @inject
    async def service(dep=Provide(get_dep)):
        return dep

    result = await service()

    assert result is picodi_registry


def test_can_pass_custom_registry_to_dependency():
    my_registry = Registry()

    def get_dep(registry):
        return registry

    @inject(registry=my_registry)
    def service(dep=Provide(get_dep)):
        return dep

    result = service()

    assert result is my_registry


async def test_can_pass_custom_registry_to_dependency_async():
    my_registry = Registry()

    async def get_dep(registry):
        return registry

    @inject(registry=my_registry)
    async def service(dep=Provide(get_dep)):
        return dep

    result = await service()

    assert result is my_registry


def test_dep_with_registry_name_and_default_resolved_like_other_deps():
    def get_dep(registry=Provide(lambda: 42)):
        return registry

    @inject
    def service(dep=Provide(get_dep)):
        return dep

    result = service()

    assert result == 42
