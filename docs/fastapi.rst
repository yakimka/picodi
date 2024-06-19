FastAPI Integration
===================

Picodi can be used with web frameworks like FastAPI, Django, Flask, etc.

Here is an example of how to use Picodi with FastAPI dependency injection system.

Using Picodi dependencies with FastAPI
--------------------------------------

If you want to use Picody dependency in FastAPI view functions,
you can use ``Depends`` with :func:`picodi.Provide`.

.. code-block:: python

    from fastapi import Depends, FastAPI
    from picodi import Provide, inject

    app = FastAPI()


    @inject
    async def get_redis_connection(port: int = Provide(lambda: 8080)) -> str:
        return "http://redis:{}".format(port)


    @app.get("/")
    @inject
    async def read_root(redis: str = Depends(Provide(get_redis_connection))):
        return {"redis": redis}


    # uvicorn fastapi_di:app --reload
    # curl http://localhost:8000/
    # Output: {"redis":"http://redis:8080"}

Combining Picodi with FastAPI dependency injection system
----------------------------------------------------------

Dependency injection system in FastAPI is very powerful and handy,
specially when you use it for parsing request data, query parameters, headers, etc.
So you can combine Picodi with FastAPI dependency injection system.

.. code-block:: python

    # picodi_deps.py
    import abc
    from dataclasses import dataclass

    from picodi import inject


    @dataclass
    class User:
        id: str
        nickname: str


    class IUserRepository(abc.ABC):
        @abc.abstractmethod
        async def get_user_by_nickname(self, nickname: str) -> User | None:
            pass


    class DummyUserRepository(IUserRepository):
        async def get_user_by_nickname(self, nickname: str) -> User | None:
            return User(id="1", nickname=nickname)


    @inject
    def get_user_repository() -> IUserRepository:
        return DummyUserRepository()

.. code-block:: python

    # fastapi_deps.py
    from typing import Annotated

    from fastapi import Depends, HTTPException
    from fastapi.security import HTTPBasic, HTTPBasicCredentials
    from picodi import Provide, inject

    from picodi_deps import IUserRepository, User, get_user_repository

    security = HTTPBasic()


    @inject
    async def get_current_user(
        # This is a dependency that will use the security scheme.
        credentials: Annotated[HTTPBasicCredentials, Depends(security)],
        # Picodi dependency need to be provided with `Provide`
        user_repo: IUserRepository = Depends(Provide(get_user_repository)),
    ) -> User:
        user = await user_repo.get_user_by_nickname(credentials.username)
        if user is None:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        return user

.. code-block:: python

    # fastapi_app.py
    from fastapi import Depends, FastAPI
    from pydantic import BaseModel

    from fastapi_deps import get_current_user
    from picodi_deps import User

    app = FastAPI()


    class UserResp(BaseModel):
        id: str
        nickname: str


    @app.get("/whoami")
    # Because `get_current_user` already injected and wrapped Picodi dependency in
    #   `Provide`, you can use it directly with `Depends`
    def whoami(current_user: User = Depends(get_current_user)) -> UserResp:
        return UserResp(id=current_user.id, nickname=current_user.nickname)


    # uvicorn fastapi_app:app --reload
    # curl http://localhost:8000/whoami -u "It\'s me Mario:password"
    # Output: {"id":"1","nickname":"It\\'s me Mario"}%
