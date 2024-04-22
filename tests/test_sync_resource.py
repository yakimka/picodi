from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from nanodi import Provide, inject, resource, shutdown_resources

if TYPE_CHECKING:
    from collections.abc import Generator


@dataclass
class Redis:
    host: str
    closed: bool = False

    def make_request(self) -> None:
        if self.closed:
            raise ValueError("Connection is closed")
        return None

    def close(self) -> None:
        self.closed = True


@pytest.fixture()
def redis_dependency():
    @resource
    def get_redis() -> Generator[Redis, None, None]:
        redis = Redis(host="localhost")
        yield redis
        redis.close()

    return get_redis


def test_resources_dont_close_automatically(redis_dependency):
    @inject
    def my_service(redis: Redis = Provide(redis_dependency)):
        redis.make_request()
        return redis

    redis = my_service()

    assert redis.closed is False


def test_resources_can_be_closed_manually(redis_dependency):
    @inject
    def my_service(redis: Redis = Provide(redis_dependency)):
        redis.make_request()
        return redis

    redis = my_service()

    shutdown_resources()
    assert redis.closed is True
