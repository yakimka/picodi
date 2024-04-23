from dataclasses import dataclass

from picodi import Provide, inject


@dataclass
class Redis:
    host: str


def get_redis() -> Redis:
    return Redis(host="localhost")


def test_resolve_dependency():
    @inject
    def my_service(redis: Redis = Provide(get_redis)):
        return redis

    redis = my_service()

    assert isinstance(redis, Redis), redis


def test_can_pass_dependency():
    @inject
    def my_service(redis: Redis | str = Provide(get_redis)):
        return redis

    redis = my_service(redis="override")

    assert redis == "override"


def test_same_dependencies_in_single_call_is_different_instances():
    @inject
    def my_service(
        redis1: Redis = Provide(get_redis), redis2: Redis = Provide(get_redis)
    ):
        return redis1, redis2

    redis1, redis2 = my_service()

    assert isinstance(redis1, Redis)
    assert isinstance(redis2, Redis)
    assert redis1 is not redis2


def test_nested_dependencies():
    @inject
    def my_service_inner(redis: Redis = Provide(get_redis)):
        return redis

    @inject
    def my_service_outer(inner_service: Redis = Provide(my_service_inner)):
        return inner_service

    inner_service = my_service_outer()

    assert isinstance(inner_service, Redis)
