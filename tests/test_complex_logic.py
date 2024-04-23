from __future__ import annotations

from picodi import Provide, inject


def get_redis() -> str:
    yield "Redis"


@inject
def get_sessions_storage(redis: str = Provide(get_redis)) -> str:
    return f"SessionsStorage({redis})"


def get_postgres_connection() -> str:
    return "Postgres"


@inject
def get_db(postgres: str = Provide(get_postgres_connection)) -> str:
    return f"{postgres} DB"


@inject
def get_users_repository(db: str = Provide(get_db)) -> str:
    return f"UsersRepository({db})"


@inject
def get_users_service(
    users_repository: str = Provide(get_users_repository),
    sessions_storage: str = Provide(get_sessions_storage),
) -> str:
    return f"UsersService({users_repository}, {sessions_storage})"


def test_resolve_complex_service():
    users_service = get_users_service()

    expected = "UsersService(UsersRepository(Postgres DB), SessionsStorage(Redis))"
    assert users_service == expected
