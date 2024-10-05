import pytest

from picodi import Provide, inject


def original_dependency():
    raise NotImplementedError


def second_original_dependency():
    raise NotImplementedError


def override_dependency():
    return 42


def second_override_dependency():
    return 24


@inject
def service(dependency=Provide(original_dependency)):
    return dependency


@pytest.mark.picodi_override(original_dependency, override_dependency)
def test_can_override_deps_with_marker():
    result = service()

    assert result == 42


@pytest.mark.picodi_override(
    [
        (original_dependency, override_dependency),
        (second_original_dependency, second_override_dependency),
    ]
)
def test_can_override_multiple_deps_with_marker():
    @inject
    def second_service(
        dependency=Provide(original_dependency),
        second_dependency=Provide(second_original_dependency),
    ):
        return dependency, second_dependency

    result = second_service()

    assert result == (42, 24)
