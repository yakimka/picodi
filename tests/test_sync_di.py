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


def test_dependencies_must_use_cache():
    @inject
    def my_service(redis: Redis = Depends(get_redis)):
        return redis

    redis1 = my_service()
    redis2 = my_service()

    assert isinstance(redis1, Redis)
    assert redis1 is redis2


def test_dependencies_must_without_cache():
    @inject
    def my_service(redis: Redis = Depends(get_redis, use_cache=False)):
        return redis

    redis1 = my_service()
    redis2 = my_service()

    assert isinstance(redis1, Redis)
    assert isinstance(redis2, Redis)
    assert redis1 is not redis2
