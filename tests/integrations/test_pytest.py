import pytest


def test_can_override_deps_with_marker(pytester):
    pytester.makeconftest(
        """
        pytest_plugins = ["picodi.integrations._pytest"]
    """
    )

    pytester.makepyfile(
        """
        import pytest
        from picodi import Provide, inject

        def original_dependency():
            raise NotImplementedError

        def override_dependency():
            return 42

        @inject
        def service(dependency=Provide(original_dependency)):
            return dependency

        @pytest.mark.picodi_override(original_dependency, override_dependency)
        def test_can_override_deps_with_marker():
            result = service()

            assert result == 42
    """
    )

    result = pytester.runpytest()

    result.assert_outcomes(passed=1)


def test_can_override_deps_with_marker_async(pytester):
    pytester.makepyprojecttoml(
        """
        [tool.coverage.run]
        branch = true
    """
    )

    pytester.makeconftest(
        """
        import coverage
        coverage.process_startup()
        pytest_plugins = [
            "picodi.integrations._pytest",
            "picodi.integrations._pytest_asyncio",
        ]
    """
    )

    pytester.makepyfile(
        """
        import pytest
        from picodi import Provide, inject

        async def original_dependency():
            raise NotImplementedError

        async def override_dependency():
            return 42

        @inject
        async def service(dependency=Provide(original_dependency)):
            return dependency

        @pytest.mark.picodi_override(original_dependency, override_dependency)
        @pytest.mark.asyncio
        async def test_can_override_deps_with_marker():
            result = await service()

            assert result == 42
    """
    )

    result = pytester.runpytest_subprocess()

    result.assert_outcomes(passed=1)


def test_can_override_multiple_deps_with_marker(pytester):
    pytester.makeconftest(
        """
        pytest_plugins = ["picodi.integrations._pytest"]
    """
    )

    pytester.makepyfile(
        """
        import pytest
        from picodi import Provide, inject

        def original_dependency():
            raise NotImplementedError

        def override_dependency():
            return 42

        def second_original_dependency():
            raise NotImplementedError

        def second_override_dependency():
            return 24

        @inject
        def service(
            dependency1=Provide(original_dependency),
            dependency2=Provide(second_original_dependency),
        ):
            return dependency1, dependency2

        @pytest.mark.picodi_override(
            [
                (original_dependency, override_dependency),
                (second_original_dependency, second_override_dependency),
            ]
        )
        def test_can_override_multiple_deps_with_marker():
            result = service()

            assert result == (42, 24)
    """
    )

    result = pytester.runpytest()

    result.assert_outcomes(passed=1)


def test_can_override_with_fixture(pytester):
    pytester.makeconftest(
        """
        pytest_plugins = ["picodi.integrations._pytest"]
    """
    )

    pytester.makepyfile(
        """
        import pytest
        from picodi import Provide, inject

        def original_dependency():
            raise NotImplementedError

        def override_dependency():
            return 42

        @inject
        def service(dependency=Provide(original_dependency)):
            return dependency

        @pytest.fixture()
        def picodi_overrides():
            return [(original_dependency, override_dependency)]

        @pytest.mark.usefixtures("picodi_overrides")
        def test_can_override_with_fixture():
            result = service()

            assert result == 42
    """
    )

    result = pytester.runpytest()

    result.assert_outcomes(passed=1)


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


def test_can_init_dependencies_with_marker(pytester):
    pytester.makeconftest(
        """
        pytest_plugins = ["picodi.integrations._pytest"]
    """
    )

    pytester.makepyfile(
        """
        import pytest
        from picodi import Provide, inject, registry, SingletonScope

        inited = False

        @registry.set_scope(SingletonScope)
        def ged_dep():
            global inited
            inited = True
            return 42

        @inject
        def service(dependency=Provide(ged_dep)):
            return dependency


        @pytest.mark.picodi_init_dependencies(dependencies=[ged_dep])
        def test_hello_default():
            assert inited is True
            assert service() == 42
    """
    )

    result = pytester.runpytest()

    result.assert_outcomes(passed=1)


def test_can_init_dependencies_with_marker_async(pytester):
    pytester.makepyprojecttoml(
        """
        [tool.coverage.run]
        branch = true
    """
    )

    pytester.makeconftest(
        """
        import coverage
        coverage.process_startup()
        pytest_plugins = [
            "picodi.integrations._pytest",
            "picodi.integrations._pytest_asyncio",
        ]
    """
    )

    pytester.makepyfile(
        """
        import pytest
        from picodi import Provide, inject, registry, SingletonScope

        inited = False

        @registry.set_scope(SingletonScope)
        async def ged_dep():
            global inited
            inited = True
            return 42

        @inject
        def service(dependency=Provide(ged_dep)):
            return dependency


        @pytest.mark.picodi_init_dependencies(dependencies=[ged_dep])
        def test_hello_default():
            assert inited is True
            assert service() == 42
    """
    )

    result = pytester.runpytest_subprocess()

    result.assert_outcomes(passed=1)


def test_cant_use_init_dependencies_with_args(pytester):
    pytester.makeconftest(
        """
        pytest_plugins = ["picodi.integrations._pytest"]
    """
    )

    pytester.makepyfile(
        """
        import pytest


        @pytest.mark.picodi_init_dependencies("position arg")
        def test_hello_default():
            pass
    """
    )

    result = pytester.runpytest()

    assert "marker don't support positional arguments" in "".join(result.outlines)


def test_cant_use_init_dependencies_without_kwargs(pytester):
    pytester.makeconftest(
        """
        pytest_plugins = ["picodi.integrations._pytest"]
    """
    )

    pytester.makepyfile(
        """
        import pytest


        @pytest.mark.picodi_init_dependencies
        def test_hello_default():
            pass
    """
    )

    result = pytester.runpytest()

    assert "marker must have keyword arguments" in "".join(result.outlines)


def test_fixtures_executes_in_strict_order(pytester):
    pytester.makeconftest(
        """
        pytest_plugins = ["picodi.integrations._pytest"]
    """
    )

    pytester.makepyfile(
        """
        import pytest
        from picodi import Provide, inject, registry, SingletonScope

        order = []

        @pytest.fixture()
        def picodi_overrides():
            order.append("picodi_overrides")
            return []

        @registry.set_scope(SingletonScope)
        def auto_init_dependency():
            order.append("auto_init_dependency")

        @pytest.mark.picodi_init_dependencies(dependencies=[auto_init_dependency])
        def test_hello_default():
            assert order == [
                "picodi_overrides",
                "auto_init_dependency",
            ]
    """
    )

    result = pytester.runpytest("-vv")

    result.assert_outcomes(passed=1)
