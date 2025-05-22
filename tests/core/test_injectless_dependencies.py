from picodi import NullScope, Provide, inject, registry


def test_can_resolve_dependencies_without_inject():

    @registry.set_scope(NullScope)
    def dep_a():
        return "a"

    @registry.set_scope(NullScope)
    def dep_b(a: str = Provide(dep_a)):
        return a + "b"

    @registry.set_scope(NullScope)
    def dep_c(b: str = Provide(dep_b)):
        return b + "c"

    @inject
    def service(
        a: str = Provide(dep_a), b: str = Provide(dep_b), c: str = Provide(dep_c)
    ):
        return a, b, c

    assert service() == ("a", "ab", "abc")
