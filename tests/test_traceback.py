import pytest

from picodi import Provide, inject


def test_traceback_should_show_actual_source_code():
    """
    Check that inject decorator don't replace traceback when error occurs in
    decorated function, and still show the actual source code that caused the error.
    """

    def get_resource():
        yield "resource"

    @inject
    def service(dep=Provide(get_resource)):
        assert dep
        1 / 0  # noqa: B018

    with pytest.raises(ZeroDivisionError) as excinfo:
        service()

    assert excinfo.traceback[-1].source.lines[-1].strip() == "1 / 0  # noqa: B018"


async def test_traceback_should_show_actual_source_code_async():
    async def get_resource():
        yield "resource"

    @inject
    async def service(dep=Provide(get_resource)):
        assert dep
        1 / 0  # noqa: B018

    with pytest.raises(ZeroDivisionError) as excinfo:
        await service()

    assert excinfo.traceback[-1].source.lines[-1].strip() == "1 / 0  # noqa: B018"


def test_should_show_actual_code_if_stop_iteration_raised_in_user_code():
    def get_resource():
        return "resource"

    @inject
    def service(dep=Provide(get_resource)):  # noqa: ARG001
        next(i for i in range(0))

    with pytest.raises(StopIteration) as excinfo:
        service()

    assert excinfo.traceback[-1].source.lines[-1].strip() == "next(i for i in range(0))"
