from picodi import Provide, inject, registry


def get_meaning_of_life() -> int:
    return 42


async def get_meaning_of_life_async() -> int:
    return 42


def test_resolve_dependency():
    @inject
    def get_dependency(num: int = Provide(get_meaning_of_life)):
        return num

    result = registry.resolve(get_dependency)

    assert result == 42


async def test_resolve_dependency_async():
    @inject
    async def get_dependency(num: int = Provide(get_meaning_of_life_async)):
        return num

    result = await registry.resolve(get_dependency)

    assert result == 42


def test_resolve_dependency_with_context_manager():
    @inject
    def get_dependency(num: int = Provide(get_meaning_of_life)):
        return num

    with registry.resolve(get_dependency) as result:
        assert result == 42
