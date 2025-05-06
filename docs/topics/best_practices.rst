.. _topics_best_practices:

##############
Best Practices
##############

Dependency injection (DI) libraries like Picodi are powerful tools for managing dependencies,
but like any tool, they can be misused.
Adhering to best practices helps you harness DI's potential while avoiding common pitfalls
that can lead to complex and hard-to-maintain code.

*************************************************
Inject Dependencies Only at the Application Edges
*************************************************

This is arguably the most important principle.
Dependencies should primarily be injected at the **outermost layers** of your
application – the points where your framework or entry script invokes your code.

*   **Web Applications:** Inject dependencies mainly in route handler functions.
    Avoid injecting them deep inside internal service functions called by the routes.
*   **CLI Applications:** Inject dependencies in the main command handler functions.
*   **Background Tasks:** Inject dependencies in the entry point function for the task.

**Why?**

*   **Clear Boundaries:** It makes the dependencies of each major component (route, command, task)
    explicit and easy to understand.
*   **Simplified Testing:** Mocking or overriding dependencies becomes much easier
    because you only need to do it at the entry points, not deep within nested function calls.
*   **Reduced Complexity:** Prevents the DI library from becoming deeply entangled
    with your core business logic.

**Example (FastAPI):**

.. testcode:: application_edges

    # --- Dependencies ---
    class Database: ...


    def get_db() -> Database: ...


    class Cache: ...


    def get_cache() -> Cache: ...


    # --- Service Layer (NO injection here) ---
    class UserService:
        # Receives dependencies via constructor, but NOT via ``@inject``
        def __init__(self, db: Database, cache: Cache):
            self.db = db
            self.cache = cache

        def get_user_profile(self, user_id: int):
            # Uses db and cache
            ...


    # --- Dependency for Service (NO injection here either) ---
    # This function *creates* the service, but doesn't use ``@inject`` itself
    # It might receive its own dependencies (db, cache) via parameters if needed,
    # but those would be injected *into this function* if it were decorated.
    # For simplicity here, assume get_db/get_cache are globally available or
    # passed differently. A better way is shown below.
    # def get_user_service(db=Provide(get_db), cache=Provide(get_cache)) -> UserService:
    #    return UserService(db=db, cache=cache)

    # --- BETTER: Inject dependencies needed to *create* the service ---
    from picodi import Provide, inject


    @inject  # Inject DB and Cache into the *service provider*
    def get_user_service(
        db: Database = Provide(get_db), cache: Cache = Provide(get_cache)
    ) -> UserService:
        # The service itself doesn't use ``@inject`` for its constructor
        return UserService(db=db, cache=cache)


    # --- FastAPI Route (Injection happens HERE) ---
    from fastapi import FastAPI
    from picodi.integrations.fastapi import Provide  # Use FastAPI version

    app = FastAPI()


    @app.get("/users/{user_id}")
    async def read_user(
        user_id: int,
        # Inject the UserService provider at the edge (route)
        user_service: UserService = Provide(get_user_service, wrap=True),
    ):
        profile = user_service.get_user_profile(user_id)
        return profile

By injecting ``UserService`` (or rather, its provider ``get_user_service``) only at the route level,
the internal ``UserService`` class remains decoupled from Picodi itself.

*****************
Use Scopes Wisely
*****************

Scopes are powerful but add complexity if misused.
Carefully consider the required lifecycle of each dependency:

*   **NullScope (Default):** Use for cheap, stateless dependencies or when a
    unique instance is strictly required per use.
*   **SingletonScope:** Use for expensive, shared resources like connection pools,
    HTTP clients, or configuration objects that should live for the entire application lifetime.
    Remember they require manual shutdown.
*   **ContextVarScope / RequestScope:** Use for resources that need to be isolated
    per request (in web apps) or per task/thread context.
    Remember they require manual shutdown, often tied to the request/task end.

Overusing singletons can lead to global state issues, while overusing ``NullScope``
can hurt performance if dependencies are expensive to create.
Choose the scope that best matches the semantics of the dependency.

************************
Keep Dependencies Simple
************************

Dependency provider functions should focus solely on **creating and configuring**
the dependency instance.
Avoid embedding complex business logic or significant side effects within them.

*   **Good:** A dependency function initializes a database connection pool or
    configures an HTTP client with base URLs and timeouts.
*   **Bad:** A dependency function that, upon creation, also makes several API calls,
    updates a database record, and sends an email.

Keep business logic in your service layer or domain model, not hidden inside dependency providers.
Dependencies are primarily infrastructure concerns.

*******************
Leverage Type Hints
*******************

While Picodi works without them (relying on ``Provide``), using Python type hints
(``-> ReturnType``, ``param: Type``) for both dependency providers and
injected parameters is strongly recommended:

*   **Readability:** Clearly documents what type of object a dependency provides or expects.
*   **Static Analysis:** Allows tools like MyPy to catch type errors early.
*   **Maintainability:** Makes the code easier to understand and refactor.

.. testcode:: type_hints

    from picodi import Provide, inject


    class MyClient: ...


    # Good: Clear type hints
    def get_my_client() -> MyClient:
        return MyClient()


    @inject
    def use_the_client(client: MyClient = Provide(get_my_client)):
        # Mypy can verify 'client' is used correctly
        ...

*********************************************************
Don't Try to Resolve Everything with Dependency Injection
*********************************************************

DI is a tool, not a silver bullet. Not every object needs to be managed by the DI library.
Ask yourself:

*   Is this object a **shared dependency** needed by multiple, unrelated parts of the application?
*   Does this object need to be **easily replaceable** (e.g., for testing, different environments)?
*   Does managing its **lifecycle** (creation, cleanup) require coordination?

If the answer to these questions is mostly "no,"
simply instantiating the class directly might be simpler and more appropriate than turning
it into a managed dependency. Overuse of DI can lead to unnecessary complexity and indirection.

For example, simple data transfer objects (DTOs) or internal helper classes within a
single service rarely need to be injected.

*************
Key Takeaways
*************

*   Inject dependencies primarily at application boundaries (routes, commands).
*   Choose scopes deliberately based on the required lifecycle and caching needs.
*   Keep dependency provider functions focused on creation/configuration, not business logic.
*   Use type hints for clarity and safety.
*   Use DI judiciously; not every object needs to be injected.

By following these practices, you can use Picodi to build robust, testable,
and maintainable applications.

This concludes the main User Guide topics. You can explore the :doc:`/api/picodi`
for detailed specifications or check the :ref:`faq` for common questions.
