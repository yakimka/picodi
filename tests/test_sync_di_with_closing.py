from collections.abc import Generator
from dataclasses import dataclass

from nanodi import Depends, inject, shutdown_resources


@dataclass
class Redis:
    host: str
    closed: bool = False

    def close(self) -> None:
        self.closed = True


def get_redis() -> Generator[Redis, None, None]:
    redis = Redis(host="localhost")
    yield redis
    redis.close()


def test_resolve_dependency():
    @inject
    def my_service(redis: Redis = Depends(get_redis)):
        return redis

    redis = my_service()

    assert isinstance(redis, Redis)


def test_close_dependency_after_call_if_not_cached():
    @inject
    def my_service(redis: Redis = Depends(get_redis, use_cache=False)):
        return redis

    redis = my_service()

    assert redis.closed is True


def test_close_dependency_globally_if_cached():
    @inject
    def my_service(redis: Redis = Depends(get_redis, use_cache=True)):
        return redis

    redis = my_service()
    assert redis.closed is False

    shutdown_resources()

    assert redis.closed is True


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
