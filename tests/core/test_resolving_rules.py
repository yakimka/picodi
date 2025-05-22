import uuid

from picodi import Provide, inject


def test_same_dependency_must_be_resolved_every_time():
    @inject
    def service(u1=Provide(uuid.uuid4), u2=Provide(uuid.uuid4)):
        return u1, u2

    u1, u2 = service()

    assert isinstance(u1, uuid.UUID)
    assert isinstance(u2, uuid.UUID)
    assert u1 != u2


def test_same_dependency_in_parent_and_child_must_be_resolved_every_time():
    @inject
    def dep_u1(u1=Provide(uuid.uuid4)):
        return u1

    @inject
    def service(u1=Provide(dep_u1), u2=Provide(uuid.uuid4)):
        return u1, u2

    u1, u2 = service()

    assert isinstance(u1, uuid.UUID)
    assert isinstance(u2, uuid.UUID)
    assert u1 != u2


def test_order_of_resolving_must_be_from_bottom_to_up_closing_from_up_to_bottom():
    context_calls = []
    numbers = iter(range(1, 200))

    def get_dep(caller: str):
        def _get_dep():
            num = next(numbers)
            context_calls.append(f"{caller} get_dep {num}")
            yield
            context_calls.append(f"{caller} close_dep {num}")

        return _get_dep

    @inject
    def get_a_dep(
        x1=Provide(get_dep("get_a_dep(x1)")), x2=Provide(get_dep("get_a_dep(x2)"))
    ):
        context_calls.append("get_a_dep")
        yield
        context_calls.append("close_a_dep")

    @inject
    def get_b_dep(x=Provide(get_dep("get_b_dep(x)")), a=Provide(get_a_dep)):
        context_calls.append("get_b_dep")
        yield
        context_calls.append("close_b_dep")

    @inject
    def service(b=Provide(get_b_dep), x=Provide(get_dep("service(x)"))):
        return None

    service()

    assert context_calls == [
        "get_b_dep(x) get_dep 1",
        "get_a_dep(x1) get_dep 2",
        "get_a_dep(x2) get_dep 3",
        "get_a_dep",
        "get_b_dep",
        "service(x) get_dep 4",
        "service(x) close_dep 4",
        "close_b_dep",
        "close_a_dep",
        "get_a_dep(x2) close_dep 3",
        "get_a_dep(x1) close_dep 2",
        "get_b_dep(x) close_dep 1",
    ]
