from picodi import ParentCallScope, Provide, dependency, inject


def test_result_cached_for_parent_and_child_scope():
    # Arrange
    nums_gen = iter(range(1, 1000))
    called = 0

    @dependency(scope_class=ParentCallScope)
    def scoped_dep():
        nonlocal called
        called += 1
        return next(nums_gen)

    @inject
    def get_a_child(num: int = Provide(scoped_dep)) -> int:
        return num

    @inject
    def get_b_child(num: int = Provide(scoped_dep)) -> int:
        return num

    @inject
    def parent(
        num: int = Provide(scoped_dep),
        a: int = Provide(get_a_child),
        b: int = Provide(get_b_child),
    ) -> list[int]:
        return [num, a, b, get_a_child(), get_b_child()]

    # Act
    result = parent()

    # Assert
    assert called == 1
    assert result == [1, 1, 1, 1, 1]


async def test_result_cached_for_parent_and_child_scope_async():
    # Arrange
    nums_gen = iter(range(1, 1000))
    called = 0

    @dependency(scope_class=ParentCallScope)
    async def scoped_dep():
        nonlocal called
        called += 1
        return next(nums_gen)

    @inject
    async def get_a_child(num: int = Provide(scoped_dep)) -> int:
        return num

    @inject
    async def get_b_child(num: int = Provide(scoped_dep)) -> int:
        return num

    @inject
    async def parent(
        num: int = Provide(scoped_dep),
        a: int = Provide(get_a_child),
        b: int = Provide(get_b_child),
    ) -> list[int]:
        return [num, a, b, await get_a_child(), await get_b_child()]

    # Act
    result = await parent()

    # Assert
    assert called == 1
    assert result == [1, 1, 1, 1, 1]


def test_result_not_cached_between_different_parent_calls():
    # Arrange
    nums_gen = iter(range(1, 1000))

    @dependency(scope_class=ParentCallScope)
    def scoped_dep():
        return next(nums_gen)

    @inject
    def parent(num: int = Provide(scoped_dep)) -> int:
        return num

    first_call = parent()

    # Act
    result = parent()

    assert first_call != result


async def test_result_not_cached_between_different_parent_calls_async():
    # Arrange
    nums_gen = iter(range(1, 1000))

    @dependency(scope_class=ParentCallScope)
    async def scoped_dep():
        return next(nums_gen)

    @inject
    async def parent(num: int = Provide(scoped_dep)) -> int:
        return num

    first_call = await parent()

    # Act
    result = await parent()

    assert first_call != result


def test_parent_call_scoped_dep_cached_only_if_injected():
    # Arrange
    nums_gen = iter(range(1, 1000))

    @dependency(scope_class=ParentCallScope)
    def scoped_dep():
        return next(nums_gen)

    @inject
    def parent(num: int = Provide(scoped_dep)) -> tuple[int, int]:
        return num, scoped_dep()

    # Act
    result = parent()
    injected_result, direct_call_result = result

    # Assert
    assert injected_result != direct_call_result


def test_teardown_called_only_after_parent_exit(closeable):
    # Arrange
    @dependency(scope_class=ParentCallScope)
    def scoped_dep():
        yield 42
        closeable.close()

    @inject
    def get_child(num: int = Provide(scoped_dep)) -> int:
        assert closeable.is_closed is False
        return num

    @inject
    def parent(
        num: int = Provide(scoped_dep),
        child_num: int = Provide(get_child),
    ) -> tuple[int, int]:
        assert closeable.is_closed is False
        return num, child_num

    # Act
    parent()

    # Assert
    assert closeable.is_closed is True
    assert closeable.close_call_count == 1


async def test_teardown_called_only_after_parent_exit_async(closeable):
    # Arrange
    @dependency(scope_class=ParentCallScope)
    async def scoped_dep():
        yield 42
        closeable.close()

    @inject
    async def get_child(num: int = Provide(scoped_dep)) -> int:
        assert closeable.is_closed is False
        return num

    @inject
    async def parent(
        num: int = Provide(scoped_dep),
        child_num: int = Provide(get_child),
    ) -> tuple[int, int]:
        assert closeable.is_closed is False
        return num, child_num

    # Act
    await parent()

    # Assert
    assert closeable.is_closed is True
    assert closeable.close_call_count == 1


def test_dependency_without_parent_call_scope_in_args_is_not_parent():
    # Arrange
    nums_gen = iter(range(1, 1000))
    called = 0

    @dependency(scope_class=ParentCallScope)
    def scoped_dep():
        nonlocal called
        called += 1
        return next(nums_gen)

    @inject
    def child(num: int = Provide(scoped_dep)) -> int:
        return num

    @inject
    def not_parent(
        some_string: int = Provide(lambda: "some_string"),
    ) -> tuple[int, int]:
        assert some_string == "some_string"
        return child(), child()

    # Act
    result = not_parent()
    first_call_result, second_call_result = result

    # Assert
    assert called == 2
    assert first_call_result != second_call_result


async def test_dependency_without_parent_call_scope_in_args_is_not_parent_async():
    # Arrange
    nums_gen = iter(range(1, 1000))
    called = 0

    @dependency(scope_class=ParentCallScope)
    async def scoped_dep():
        nonlocal called
        called += 1
        return next(nums_gen)

    @inject
    async def child(num: int = Provide(scoped_dep)) -> int:
        return num

    @inject
    async def not_parent(
        some_string: int = Provide(lambda: "some_string"),
    ) -> tuple[int, int]:
        assert some_string == "some_string"
        return await child(), await child()

    # Act
    result = await not_parent()
    first_call_result, second_call_result = result

    # Assert
    assert called == 2
    assert first_call_result != second_call_result
