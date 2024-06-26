from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from httpx import AsyncClient

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@pytest.fixture()
async def asgi_client(app, test_server_url) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(app=app, base_url=test_server_url) as client:
        yield client


@pytest.fixture()
def test_server_url():
    return "http://test"
