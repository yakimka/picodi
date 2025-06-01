from picodi import registry


def test_resolve_dependencies():
    state = []

    def foo():
        state.append("init foo")
        yield "foo"
        state.append("close foo")

    result = registry.resolve(foo)

    assert state == []
    with result as value:
        assert state == ["init foo"]
        assert value == "foo"

    assert state == ["init foo", "close foo"]


async def test_resolve_dependencies_async():
    state = []

    def foo():
        state.append("init foo")
        yield "foo"
        state.append("close foo")

    result = registry.aresolve(foo)

    assert state == []
    async with result as value:
        assert state == ["init foo"]
        assert value == "foo"

    assert state == ["init foo", "close foo"]


async def test_resolve_sync_dependencies_async():
    state = []

    def foo():
        state.append("init foo")
        yield "foo"
        state.append("close foo")

    result = registry.aresolve(foo)

    assert state == []
    async with result as value:
        assert state == ["init foo"]
        assert value == "foo"

    assert state == ["init foo", "close foo"]
