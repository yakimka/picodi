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


@pytest.fixture()
def picodi_overrides():
    return [(original_dependency, override_dependency)]


@pytest.mark.usefixtures("picodi_overrides")
def test_can_override_with_fixture():
    result = service()

    assert result == 42


def test_cant_add_more_tan_2_arguments_to_marker(pytester):
    pytester.makeconftest(
        """
        pytest_plugins = ["picodi.integrations._pytest"]
    """
    )

    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.picodi_override(1, 2, 3)
        def test_hello_default():
            assert True
    """
    )

    result = pytester.runpytest()

    assert "marker must have 2 arguments" in "".join(result.outlines)


def test_single_argument_cant_be_not_list_or_tuple(pytester):
    pytester.makeconftest(
        """
        pytest_plugins = ["picodi.integrations._pytest"]
    """
    )

    pytester.makepyfile(
        """
        import pytest

        @pytest.mark.picodi_override({})
        def test_hello_default():
            assert True
    """
    )

    result = pytester.runpytest()

    assert "Overrides must be a list or tuple" in "".join(result.outlines)


@pytest.mark.parametrize(
    "dep,override",
    [
        ("'not_callable'", "lambda: 42"),
        ("lambda: 42", "'not_callable'"),
        ("'not_callable'", "'not_callable'"),
    ],
)
def test_dependencies_and_overrides_must_be_callable(pytester, dep, override):
    pytester.makeconftest(
        """
        pytest_plugins = ["picodi.integrations._pytest"]
    """
    )

    pytester.makepyfile(
        f"""
        import pytest

        @pytest.mark.picodi_override({dep}, {override})
        def test_hello_default():
            assert True
    """
    )

    result = pytester.runpytest()

    assert "Dependency and override must be callable" in "".join(result.outlines)
