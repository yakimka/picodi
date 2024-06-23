FastAPI Integration
===================

Picodi can be used with web frameworks like FastAPI, Django, Flask, etc.

Here is an example of how to use Picodi with FastAPI dependency injection system.

Why I need additional DI library when FastAPI already has DI system?
---------------------------------------------------------------------

FastAPI built-in dependency injection system lacks some features that Picodi provides.
For example, Picodi allows you to use scopes for your dependencies.
This is useful when you want to manage the lifecycle of your dependencies.
Another drawback of FastAPI dependency injection system is that it works only
in FastAPI views. If you want to use dependencies in other parts of your
application, like workers, cli commands, etc., you need to pass them manually.

Picodi is a general-purpose dependency injection library that works with any
Python application. It provides a more flexible dependencies.
You can use it with FastAPI, Django, Flask, or any other Python framework.

Picodi doesn't replace FastAPI DI system entirely. You can
use Picodi for dependencies that require more control over their lifecycle
or\\and can be used outside of FastAPI views. You still can use FastAPI DI
for parsing request data, query parameters, headers, etc.

Using Picodi dependencies with FastAPI
--------------------------------------

If you want to use Picody dependency in FastAPI view functions,
you can use ``Depends`` with :func:`picodi.Provide`.

.. testcode::

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

Request-scoped dependencies
---------------------------

Picodi doesn't provide integrations for frameworks (at least for now), but you can
create your own request-scoped dependencies using `ContextVarScope`.

Create dependency with ``ContextVarScope`` scope (it will be our request-scoped dependency):

.. testcode::

    from picodi import ContextVarScope, dependency


    @dependency(scope_class=ContextVarScope)
    def get_request_scoped_cache() -> dict:
        return {}

Create middleware that will initialize and cleanup our request-scoped dependency:

.. testcode::

    from fastapi import FastAPI

    import picodi

    app = FastAPI()


    @app.middleware("http")
    async def manage_request_scoped_deps(request, call_next):
        await picodi.init_dependencies(scope_class=picodi.ContextVarScope)
        response = await call_next(request)
        await picodi.shutdown_dependencies(scope_class=picodi.ContextVarScope)
        return response

Now you can use ``get_request_scoped_cache`` dependency that will be request-scoped.

If you use ``ContextVarScope`` for another purpose, you can create your own scope class by
subclassing ``ContextVarScope``.

.. testcode::

    from picodi import ContextVarScope


    # Replace `ContextVarScope` with this class in previous examples
    class FastAPIRequestScope(ContextVarScope):
        pass


Example FastAPI application with Picodi
----------------------------------------

Here is an more complex example of a FastAPI application
that uses Picodi for dependency injection:

`Picodi FastAPI Example <https://github.com/yakimka/picodi-fastapi-example>`_
