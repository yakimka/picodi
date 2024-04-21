from __future__ import annotations

from nanodi import Depends, inject


def get_redis() -> str:
    yield "Redis"


@inject
def get_sessions_storage(redis: str = Depends(get_redis)) -> str:
    return f"SessionsStorage({redis})"


def get_postgres_connection() -> str:
    return "Postgres"


@inject
def get_db(postgres: str = Depends(get_postgres_connection)) -> str:
    return f"{postgres} DB"


@inject
def get_users_repository(db: str = Depends(get_db)) -> str:
    return f"UsersRepository({db})"


@inject
def get_users_service(
    users_repository: str = Depends(get_users_repository),
    sessions_storage: str = Depends(get_sessions_storage),
) -> str:
    return f"UsersService({users_repository}, {sessions_storage})"


def test_resolve_complex_service():
    users_service = get_users_service()

    expected = "UsersService(UsersRepository(Postgres DB), SessionsStorage(Redis))"
    assert users_service == expected
