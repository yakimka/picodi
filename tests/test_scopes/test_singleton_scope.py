import pytest

from picodi import SingletonScope


@pytest.fixture()
def sut():
    return SingletonScope()


def test_can_store_and_then_get_value(sut):
    sut.set("key", "value")

    assert sut.get("key") == "value"


def test_store_cleared_after_shutdown(sut):
    sut.set("key", "value")
    sut.shutdown()

    with pytest.raises(KeyError):
        sut.get("key")


def test_can_use_store_again_after_shutdown(sut):
    sut.set("key", "value")
    sut.shutdown()

    sut.set("key", "value")
    assert sut.get("key") == "value"
