import pytest

from picodi import SingletonScope


@pytest.fixture()
def sut():
    return SingletonScope()


def test_can_store_and_then_get_value(sut):
    sut.set("key", "value", global_key=test_can_store_and_then_get_value)

    assert sut.get("key", global_key=test_can_store_and_then_get_value) == "value"


def test_store_cleared_after_shutdown(sut):
    sut.set("key", "value", global_key=test_store_cleared_after_shutdown)
    sut.shutdown(global_key=test_store_cleared_after_shutdown)

    with pytest.raises(KeyError):
        sut.get("key", global_key=test_store_cleared_after_shutdown)


def test_can_use_store_again_after_shutdown(sut):
    sut.set("key", "value", global_key=test_can_use_store_again_after_shutdown)
    sut.shutdown(global_key=test_can_use_store_again_after_shutdown)

    sut.set("key", "value", global_key=test_can_use_store_again_after_shutdown)
    assert sut.get("key", global_key=test_can_use_store_again_after_shutdown) == "value"
