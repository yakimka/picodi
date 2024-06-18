from contextlib import nullcontext

import pytest

from picodi import ManualScope


@pytest.fixture()
def manual_scope():
    class MyManualScope(ManualScope):
        pass

    return MyManualScope()


async def test_manual_scope_enter_shutdown(manual_scope):
    assert await manual_scope.enter(nullcontext()) is None
    assert await manual_scope.shutdown() is None
