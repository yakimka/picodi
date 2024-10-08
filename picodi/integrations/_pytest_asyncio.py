from __future__ import annotations

from typing import TYPE_CHECKING

import pytest_asyncio

from picodi import init_dependencies, shutdown_dependencies

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@pytest_asyncio.fixture()
async def _picodi_shutdown() -> AsyncGenerator[None, None]:
    """
    Shutdown dependencies after the test (async version).
    Need for tests consistency.
    """
    yield
    await shutdown_dependencies()


@pytest_asyncio.fixture()
async def _picodi_init_dependencies(
    picodi_init_dependencies_kwargs: dict | None,
) -> None:
    if picodi_init_dependencies_kwargs is None:
        return
    await init_dependencies(**picodi_init_dependencies_kwargs)
