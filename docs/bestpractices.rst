Best practices
==============

Dependency injection (DI) libraries, including Picodi, are powerful tools for managing
dependencies in your applications. However, misusing them can lead to code that is
difficult to maintain and understand. By adhering to best practices, you can harness
DI's potential while avoiding common pitfalls.

Inject Dependencies Only at the Application’s Edges
---------------------------------------------------

Dependencies should be injected only at the outermost layers of your
application—specifically, in functions directly invoked by the framework or the user.

For instance, in FastAPI, dependencies should be injected in route handlers,
not in the internal functions those handlers call.
Similarly, for CLI commands or background tasks,
inject dependencies in the entry points, such as the main function.

This practice promotes:

- Clear separation of concerns: It becomes easier to understand which dependencies
  each route, command, or task requires.
- Simplified testing: Mocking dependencies is straightforward since you don’t need to
  override them deep within the application.

By adhering to this rule, you ensure that the flow of your application
remains comprehensible and maintainable.

Use Scopes Wisely
-----------------

Scopes are a powerful but potentially complex feature in DI libraries.
Mismanaging scopes can lead to bugs and unnecessary complexity.

When defining a dependency, carefully consider its lifecycle:

- Use request scope for dependencies that should be created anew with each request.
- Use singleton scope for dependencies that must be shared across the entire application.

Choosing the correct scope ensures efficient resource usage and helps maintain
predictable behavior in your application.

Keep Dependencies Simple
------------------------

Dependencies should remain straightforward, focusing only on what is necessary for
their purpose.
Avoid introducing complex logic or side effects in your dependencies.
Instead, encapsulate business logic within your application’s core code.

This principle makes your application:

- Easier to understand.
- More maintainable.

Remember: dependencies are infrastructure components, not the place for application logic.

Leverage Type Hints
-------------------

Although Picodi does not mandate the use of type hints, incorporating them is a best
practice that improves code quality. Type hints enhance:

- Error detection: By catching mismatches early during development.
- Readability: Clearly conveying the types of arguments and return values.

When defining dependencies, always include type hints to explicitly specify their
inputs and outputs. This clarity aids both developers and tools that analyze your code.

Don’t Try to Resolve Everything with Dependency Injection
---------------------------------------------------------

Dependency Injection (DI) is a powerful tool, but it’s not a universal solution for
every scenario.
In some cases, using DI can introduce unnecessary complexity
rather than simplifying your code.

If a class is neither a shared dependency nor requires substitution for testing or
alternative implementations, injecting it might be unnecessary.
In such instances, directly instantiating the class within your application
can lead to simpler and more straightforward code.

When used judiciously, DI enables the creation of robust, testable,
and maintainable applications.
By following best practices and carefully evaluating when DI is truly beneficial,
you can ensure that it serves as an effective tool in your development process
rather than a source of over-engineering.
