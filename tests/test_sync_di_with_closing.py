from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pytest

from picodi import Provide, inject

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


def get_redis() -> Generator[Redis, None, None]:
    redis = Redis(host="localhost")
    yield redis
    redis.close()


def test_resolve_dependency():
    @inject
    def my_service(redis: Redis = Provide(get_redis)):
        return redis

    redis = my_service()

    assert isinstance(redis, Redis)


@pytest.mark.parametrize("use_cache", [True, False])
def test_close_dependency_after_call(use_cache):
    @inject
    def my_service(redis: Redis = Provide(get_redis, use_cache=use_cache)):
        redis.make_request()
        return redis

    redis = my_service()

    assert redis.closed is True
