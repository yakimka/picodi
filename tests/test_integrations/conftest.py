from __future__ import annotations

from typing import TYPE_CHECKING

import pytest
from httpx import AsyncClient

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@pytest.fixture()
async def asgi_client(app) -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
