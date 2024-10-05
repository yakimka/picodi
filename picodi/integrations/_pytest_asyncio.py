from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from picodi import shutdown_dependencies

if TYPE_CHECKING:
    from collections.abc import AsyncGenerator


@pytest.fixture()
async def _picodi_shutdown() -> AsyncGenerator[None, None]:
    """
    Shutdown dependencies after the test (async version).
    Need for tests consistency.
    """
    yield
    await shutdown_dependencies()
