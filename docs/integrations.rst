Integrations
=============

Picodi can be used with web frameworks like FastAPI, Django, Flask, etc.

Below you can find some useful integrations that Picodi provides.

Starlette
---------

If you want to use request scope in your Starlette application,
you can use the ``RequestScopeMiddleware`` middleware.

.. testcode::

    from starlette.applications import Starlette
    from starlette.middleware import Middleware
    from picodi.integrations.starlette import RequestScopeMiddleware

    app = Starlette(middleware=[Middleware(RequestScopeMiddleware)])


And now you can use the ``RequestScope`` scope for your dependencies.
Dependencies will be resolved in the context of the current request.

.. testcode::

    from picodi import dependency
    from picodi.integrations.starlette import RequestScope


    @dependency(scope_class=RequestScope)
    def get_cache(): ...


FastAPI
-------

Why I need additional DI library when FastAPI already has DI system?
*********************************************************************

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
**************************************

If you want to use Picody dependency in FastAPI view functions,
you can use ``Depends`` with :func:`picodi.integrations.fastapi.Provide`.

.. testcode::

    from fastapi import Depends, FastAPI
    from picodi import inject
    from picodi.integrations.fastapi import Provide

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

Injecting dependencies in FastAPI views without ``@inject``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``Depends(Provide(...))`` looks a bit verbose, if you want to make it shorter,
you can use a ``wrap`` parameter of :func:`picodi.integrations.fastapi.Provide`.

Also because FastAPI already has mechanism of resolving dependencies, we can use it
without need to use ``@inject`` decorator, just pass ``wrap=True``
to :func:`picodi.integrations.fastapi.Provide`. This is preferred way to use Picodi
dependencies in FastAPI views.

.. testcode::

    @app.get("/")
    async def read_root(redis: str = Provide(get_redis_connection, wrap=True)):
        pass

Combining Picodi with FastAPI dependency injection system
*********************************************************

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
    from picodi import inject
    from picodi.integrations.fastapi import Provide

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
***************************

Like with Starlette you can use request scope in FastAPI application.

.. testcode::

    from fastapi import FastAPI
    from picodi import dependency
    from picodi.integrations.fastapi import RequestScope, RequestScopeMiddleware

    app = FastAPI(middleware=[Middleware(RequestScopeMiddleware)])


    # Now you can use the RequestScope scope for your dependencies.
    # Dependencies will be initialized once per request
    #   and closed after the request is finished.
    @dependency(scope_class=RequestScope)
    def get_cache():
        pass

Example FastAPI application with Picodi
****************************************

Here is an more complex example of a FastAPI application
that uses Picodi for dependency injection:

`Picodi FastAPI Example <https://github.com/yakimka/picodi-fastapi-example>`_

Pytest
------

About ``pytest`` integration you can read at :doc:`testing`
