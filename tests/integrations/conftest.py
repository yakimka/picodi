from __future__ import annotations

import contextlib

import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture()
async def make_asgi_client(test_server_url):
    @contextlib.asynccontextmanager
    async def maker(app):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url=test_server_url, timeout=2
        ) as client:
            yield client

    return maker


@pytest.fixture()
def test_server_url():
    return "http://test"
