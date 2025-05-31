from picodi import Provide, SingletonScope, inject, registry


def test_can_resolve_dependencies_without_inject():
    def dep_a():
        return "a"

    def dep_b(a: str = Provide(dep_a)):
        return a + "b"

    def dep_c(b: str = Provide(dep_b)):
        return b + "c"

    @inject
    def service(
        a: str = Provide(dep_a), b: str = Provide(dep_b), c: str = Provide(dep_c)
    ):
        return a, b, c

    assert service() == ("a", "ab", "abc")


async def test_can_resolve_dependencies_without_inject_async():
    async def dep_a():
        return "a"

    async def dep_b(a: str = Provide(dep_a)):
        return a + "b"

    async def dep_c(b: str = Provide(dep_b)):
        return b + "c"

    @inject
    async def service(
        a: str = Provide(dep_a), b: str = Provide(dep_b), c: str = Provide(dep_c)
    ):
        return a, b, c

    assert await service() == ("a", "ab", "abc")


def test_can_init_dependencies_without_inject():
    results = []

    def dep_a():
        return "a"

    @registry.set_scope(SingletonScope, auto_init=True)
    def dep_b(a: str = Provide(dep_a)):
        result = a + "b"
        results.append(result)
        return result

    registry.init()

    assert results == ["ab"]


async def test_can_init_dependencies_without_inject_async():
    results = []

    def dep_a():
        return "a"

    @registry.set_scope(SingletonScope, auto_init=True)
    async def dep_b(a: str = Provide(dep_a)):
        result = a + "b"
        results.append(result)
        return result

    await registry.init()

    assert results == ["ab"]
