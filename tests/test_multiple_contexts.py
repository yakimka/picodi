from __future__ import annotations

from typing import TYPE_CHECKING

from picodi import Context, Provide, SingletonScope, inject

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


class Resource:
    def __init__(self):
        self.name = "default"
        self.closed = True

    def open(self):
        if not self.closed:
            raise RuntimeError("Resource is already open")
        self.closed = False

    def close(self):
        if self.closed:
            raise RuntimeError("Resource is already closed")
        self.closed = True

    def action(self) -> None:
        if self.closed:
            raise RuntimeError("Resource is closed")
        return None


async def get_resource() -> AsyncGenerator[Resource, None]:
    resource = Resource()
    resource.open()
    yield resource
    resource.close()


@inject
async def service(resource: Resource = Provide(get_resource)) -> Resource:
    assert not resource.closed
    return resource


async def test_can_use_multiple_non_overlapping_contexts():
    api_ctx = Context((get_resource, SingletonScope), init_dependencies=[get_resource])
    cli_ctx = Context((get_resource, SingletonScope), init_dependencies=[get_resource])

    async with api_ctx:
        api_resource = await service()
        assert api_resource.name == "default"
        api_resource.name = "api"

        async with cli_ctx:
            cli_resource = await service()
            assert cli_resource.name == "default"
            cli_resource.name = "cli"

        api_resource = await service()
        assert api_resource.name == "api"
