from dataclasses import dataclass

from nanodi import Depends, inject


@dataclass
class Redis:
    host: str


def get_redis() -> Redis:
    return Redis(host="localhost")


def test_resolve_dependency():
    @inject
    def my_service(redis: Redis = Depends(get_redis)):
        return redis

    redis = my_service()

    assert isinstance(redis, Redis)


def test_dependencies_in_single_call_must_use_cache():
    @inject
    def my_service(
        redis1: Redis = Depends(get_redis), redis2: Redis = Depends(get_redis)
    ):
        return redis1, redis2

    redis1, redis2 = my_service()

    assert isinstance(redis1, Redis)
    assert redis1 is redis2


def test_dependencies_dont_share_cache_between_calls():
    @inject
    def my_service(redis: Redis = Depends(get_redis)):
        return redis

    redis1 = my_service()
    redis2 = my_service()

    assert isinstance(redis1, Redis)
    assert isinstance(redis2, Redis)
    assert redis1 is not redis2


def test_dependencies_in_single_call_dont_use_cache_if_specified():
    @inject
    def my_service(
        redis1: Redis = Depends(get_redis, use_cache=False),
        redis2: Redis = Depends(get_redis, use_cache=False),
    ):
        return redis1, redis2

    redis1, redis2 = my_service()

    assert isinstance(redis1, Redis)
    assert isinstance(redis2, Redis)
    assert redis1 is not redis2


def test_nested_dependencies():
    @inject
    def my_service_inner(redis: Redis = Depends(get_redis)):
        return redis

    @inject
    def my_service_outer(inner_service: Redis = Depends(my_service_inner)):
        return inner_service

    inner_service = my_service_outer()

    assert isinstance(inner_service, Redis)
