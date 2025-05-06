.. _topics_integrations:

######################
Framework Integrations
######################

While Picodi is a general-purpose dependency injection library usable in any Python application,
it also provides specific integrations to work smoothly with popular web frameworks like Starlette and FastAPI.

****************
General Approach
****************

The core principles of Picodi (``@inject``, ``Provide``, scopes, overrides) work the same regardless of the framework.
You typically inject dependencies into your framework's entry points, such as:

*   Route handlers (views) in web frameworks.
*   Command handlers in CLI applications.
*   Task functions in background workers.

Picodi's specific integrations often provide helpers like custom scopes (e.g., request scope) or
middleware to manage dependency lifecycles within the framework's context.

*********************
Starlette Integration
*********************

Picodi provides helpers for Starlette applications, primarily for managing request-scoped dependencies.

``RequestScope``
================
*   **Class:** :class:`~picodi.integrations.starlette.RequestScope`
*   **Inherits from:** :class:`~picodi.ContextVarScope`
*   **Behavior:** Creates and caches dependency instances within the context of a single HTTP request.
    Each request gets its own set of instances for dependencies using this scope.
*   **Cleanup:** Requires manual shutdown, typically handled by the
    :class:`~picodi.integrations.starlette.RequestScopeMiddleware`.

``RequestScopeMiddleware``
==========================
*   **Class:** :class:`~picodi.integrations.starlette.RequestScopeMiddleware`
*   **Purpose:** An ASGI middleware that automatically handles the lifecycle of ``RequestScope`` dependencies.

    *   It can optionally initialize specified dependencies at the start of a request using ``registry.init()``.
    *   It automatically calls ``registry.shutdown(scope_class=RequestScope)`` at the end of the
        request to clean up any request-scoped yield dependencies.

**Usage:**

1.  **Define** your request-scoped dependency using ``@registry.set_scope(RequestScope)``.
2.  **Add** the ``RequestScopeMiddleware`` to your Starlette application.

.. code-block:: python

    # dependencies.py
    from picodi import registry
    from picodi.integrations.starlette import RequestScope
    import uuid


    @registry.set_scope(RequestScope)
    def get_request_id():
        req_id = str(uuid.uuid4())
        print(f"REQUEST SCOPE: Generated request ID: {req_id}")
        yield req_id  # Use yield if cleanup needed, otherwise return
        print(f"REQUEST SCOPE: Cleaning up request ID: {req_id}")


    # app.py
    from picodi import Provide, inject
    from picodi.integrations.starlette import RequestScopeMiddleware
    from starlette.applications import Starlette
    from starlette.middleware import Middleware
    from starlette.requests import Request
    from starlette.responses import JSONResponse
    from starlette.routing import Route

    from dependencies import get_request_id


    @inject
    def service(request_id: str = Provide(get_request_id)):
        return request_id


    @inject
    async def homepage(_: Request, request_id: str = Provide(get_request_id)):
        # The request_id will be unique per request
        request_id_from_service = service()
        return JSONResponse(
            {
                "request_id": request_id,
                "request_id_from_service": request_id_from_service,
            }
        )


    routes = [
        Route("/", homepage),
    ]

    # Add the middleware
    middleware = [
        Middleware(RequestScopeMiddleware)
        # You can optionally pass dependencies_for_init to the middleware
        # Middleware(RequestScopeMiddleware, dependencies_for_init=[dep1, dep2])
    ]

    app = Starlette(routes=routes, middleware=middleware)

    # Run with: uvicorn app:app
    # Accessing '/' will show the same request_id from the service and the view
    # this is because `get_request_id` has `RequestScope` scope

********************************
FastAPI Integration
********************************

FastAPI has its own powerful dependency injection system, primarily focused on route parameters, validation,
and request data parsing. Picodi can complement FastAPI's system, especially for managing application-level services,
shared resources, and complex dependency lifecycles that extend beyond a single request or need to be used outside of route handlers.

Why Use Picodi with FastAPI?
============================
*   **Scopes:** Manage dependency lifecycles beyond FastAPI's default (which is similar to Picodi's :class:`~picodi.NullScope`).
    Use :class:`~picodi.SingletonScope` for shared clients,
    :class:`~picodi.ContextVarScope`/:class:`~picodi.integrations.fastapi.RequestScope` for request-level caching.
*   **Consistency:** Use the same DI mechanism for dependencies shared between FastAPI routes, background tasks, CLI commands, etc.
*   **Testability:** Leverage Picodi's overriding capabilities for application-level services.

Using Picodi Dependencies in FastAPI Routes
===========================================

Picodi provides a special :func:`~picodi.integrations.fastapi.Provide` marker designed for FastAPI.

**Method 1: Using @inject (Less Common in Routes)**

You can use Picodi's standard ``@inject`` on your route function, but you still need to wrap the
``Provide`` marker with FastAPI's ``Depends``.

.. code-block:: python

    from fastapi import FastAPI, Depends
    from picodi import inject
    from picodi.integrations.fastapi import Provide  # Use the fastapi version

    app = FastAPI()


    # Assume get_my_service is a Picodi dependency (sync or async)
    def get_my_service():
        print("Providing my_service")
        return "My Service Instance"


    @app.get("/inject-route")
    @inject  # Picodi's inject
    async def route_with_inject(
        # Need Depends() around Picodi's Provide()
        service_instance: str = Depends(Provide(get_my_service)),
    ):
        return {"service": service_instance}

**Method 2: Using Provide(..., wrap=True) (Recommended for Routes)**

To avoid the verbosity of ``Depends(Provide(...))`` and the need for ``@inject`` on the route itself,
use the ``wrap=True`` argument with ``picodi.integrations.fastapi.Provide``.
This tells Picodi to wrap the dependency in a way that FastAPI's own DI system understands directly.

.. code-block:: python

    from fastapi import FastAPI
    from picodi.integrations.fastapi import Provide  # Use the fastapi version

    app = FastAPI()


    # Assume get_my_service is defined as before
    def get_my_service():
        print("Providing my_service")
        return "My Service Instance"


    @app.get("/wrapped-route")
    async def route_without_inject(
        # No @inject needed on the route!
        # Provide(..., wrap=True) integrates with FastAPI's DI
        service_instance: str = Provide(get_my_service, wrap=True)
    ):
        return {"service": service_instance}

This is the **preferred** way to inject Picodi-managed dependencies into FastAPI route functions,
as it leverages FastAPI's DI for the route parameters while using Picodi for managing the dependency itself.

Combining FastAPI ``Depends`` and Picodi ``Provide``
====================================================
You can easily combine FastAPI's dependencies (for things like path parameters, query parameters, security)
with Picodi dependencies within the same function signature.

.. code-block:: python

    from fastapi import FastAPI, Depends, Path, HTTPException
    from picodi.integrations.fastapi import Provide
    from typing import Annotated

    app = FastAPI()


    # --- Picodi Dependency ---
    class DatabaseClient:
        def get_item(self, item_id: int):
            print(f"DB Client: Fetching item {item_id}")
            if item_id == 42:
                return {"id": item_id, "name": "Widget"}
            return None


    def get_db_client():
        return DatabaseClient()


    # --- FastAPI Security Dependency ---
    def get_current_user(token: str | None = None):  # Example security dep
        if token == "secret":
            return {"username": "alice"}
        raise HTTPException(status_code=401, detail="Invalid token")


    # --- Route Combining Both ---
    @app.get("/items/{item_id}")
    async def get_item(
        # FastAPI path parameter
        item_id: Annotated[int, Path(title="The ID of the item to get")],
        # FastAPI security dependency
        current_user: Annotated[dict, Depends(get_current_user)],
        # Picodi dependency using ``wrap=True``
        db: DatabaseClient = Provide(get_db_client, wrap=True),
    ):
        print(f"User {current_user['username']} requesting item {item_id}")
        item = db.get_item(item_id)
        if not item:
            raise HTTPException(status_code=404, detail="Item not found")
        return item

Request-Scoped Dependencies in FastAPI
======================================
You can use the same :class:`~picodi.integrations.fastapi.RequestScopeMiddleware` and
:class:`~picodi.integrations.fastapi.RequestScope`
in FastAPI as you would in Starlette to manage request-scoped dependencies.

.. code-block:: python

    import uuid

    from fastapi import FastAPI
    from picodi import registry
    from picodi.integrations.fastapi import Provide, RequestScope, RequestScopeMiddleware
    from starlette.middleware import Middleware


    # Define request-scoped dependency
    @registry.set_scope(RequestScope)
    def get_request_correlation_id():
        req_id = str(uuid.uuid4())[:8]
        print(f"FastAPI Request Scope: Generated ID: {req_id}")
        yield req_id
        print(f"FastAPI Request Scope: Cleaning up ID: {req_id}")


    # Add middleware to FastAPI app
    app = FastAPI(middleware=[Middleware(RequestScopeMiddleware)])


    @app.get("/request-id")
    async def get_id(correlation_id: str = Provide(get_request_correlation_id, wrap=True)):
        return {"correlation_id": correlation_id}

FastAPI Example Project
=======================
For a more comprehensive example of using Picodi with FastAPI, including different scopes and testing setups,
see the example project:

`Picodi FastAPI Example <https://github.com/yakimka/picodi-fastapi-example>`_

****************
Key Takeaways
****************

*   Picodi integrates with Starlette and FastAPI, primarily via middleware and specialized ``Provide`` markers.
*   Use ``RequestScopeMiddleware`` and ``RequestScope`` for request-scoped dependencies in Starlette/FastAPI.
*   In FastAPI, use ``picodi.integrations.fastapi.Provide(..., wrap=True)`` to inject Picodi dependencies into routes without needing ``@inject`` on the route function.
*   Combine FastAPI's ``Depends`` with Picodi's ``Provide`` for flexible dependency management in routes.

Next, let's review some :ref:`Best Practices <topics_best_practices>` for using Picodi effectively.
