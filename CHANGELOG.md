# Version history

We follow [Semantic Versions](https://semver.org/).

## Version next

## Version 0.36.1

- Add more overloads for `registry.aresolve`

## Version 0.36.0

- Breaking changes:
  - `registry.resolve` and `registry.aresolve` now accept only one argument

## Version 0.35.0

- Registry is available as `registry` arg in dependency functions

## Version 0.34.0

- Breaking changes:
  - `registry.resolve` and `registry.aresolve` now accept variadic arguments
  - Context managers of `registry.resolve` and `registry.aresolve` will return
    dependency value if only one dependency is requested, otherwise they will return
    a tuple of values

## Version 0.33.0

- Rewrite resolving logic
- You don’t have to use the @inject decorator for nested dependencies;
  it’s only required for top-level calls. Applying @inject to nested dependencies is entirely optional.
- rewrite RequestScope for starlette and fastapi
- Breaking changes:
  - removed `enter` and `shutdown` methods from `AutoScope` class

## Version 0.32.2

- Shield resource cleanup

## Version 0.32.1

- Fix error when returning custom context manager from dependency cause error

## Version 0.32.0

- Fix incorrect line number in traceback for decorated function
- Picodi now can use `contextlib` dependencies like yield functions
- Changed state management of registry
- Breaking changes:
  - renamed `helpers.enter` to `helpers.resolve`
  - deleted `dependency`, `init_dependencies`, `shutdown_dependencies` in favor of
    `registry.set_scope`, `registry.init`, `registry.shutdown`
  - deleted `helpers.lifespan` in favor of `registry.lifespan` and `registry.alifespan`
  - registry.override now can't be used as decorator

## Version 0.31.0

- Breaking changes:
  - argument `init_scope` of `init_dependencies` replaces with `dependecies` argument
  - removed `use_init_hook` argument of `dependency` decorator
  - manual dependencies no longer implicitly initialized when `init_dependencies` called
    instead, you should pass them to `init_dependencies` explicitly. These changes
    also apply to `lifespan` decorator and another helpers.

## Version 0.30.0

- Now you can use picodi dependencies in FastAPI views without need to
  decorate view with `@inject`.

## Version 0.29.0

- Support for Python 3.13

## Version 0.28.2

- Change order of running pytest fixtures

## Version 0.28.1

- Rename pytest fixture name for consistency

## Version 0.28.0

- Removed dead code
- Added `init_dependencies` marker for pytest
- Added tests for detecting race conditions
- Added Python 3.13-free-threading to CI

## Version 0.27.0

- Breaking changes:
  - Argument `ignore_manual_init` of `@dependency` decorator renamed to `use_init_hook`
  and its default value set to `False`

## Version 0.26.0

- Rewrite `helpers.enter` as class-based context manager (now it behaves more predictably)
- Added `registry.touched` property and `registry.clear_touched` method for tracking
dependencies usage (useful for testing)
- Added pytest integration for simpler testing

## Version 0.25.0

- Patch dependency tree when resolving dependencies with overrides
- Breaking changes:
  - If you try to override a dependency that is already is use in another override, you will get an error

## Version 0.24.0

- revert tags

## Version 0.23.0

- Now you can mark you dependencies with tags for more granular control over their lifecycle
- Breaking changes:
  - Removed `ignore_manual_init` argument from `dependency` decorator
  - `lifespan` now has new signature

## Version 0.22.0

- `enter` now respects overrides
- `lifespan` is a factory decorator now

## Version 0.21.0

- Make `Dependency.__call__` async because FastAPI always runs Picodi deps in threadpool even if they are async
- Rename `Dependency` to `Depends` [internal change]
- Run mypy in tests directory
- Make sure that `inject` doesn't change type of wrapped function (e.g. coroutinefunction, generatorfunction, etc.)
- Added Starlette integration
- Added FastAPI integration
- Breaking changes:
  - Return value of `Provide` no longer has `__call__` method

## Version 0.20.0

- Fixed bug with contextvars when `init_dependencies` run in different context
- Breaking changes:
  - Changed default scope class of `init_dependencies` and `shutdown_dependencies` to `SingletonScope

## Version 0.19.0

- `ignore_manual_init` argument of `dependency` decorator now can be callable type

## Version 0.18.0

- Added `helpers.enter` context manager for resolving dependencies in pytest fixtures

## Version 0.17.1

- Fixed typehints
- Fixed rare error when `shutdown_dependencies` raises "RuntimeError: There is no current event loop"

## Version 0.17.0

- Updated docstrings

## Version 0.16.0

- Added `ignore_manual_init` option to `dependency` decorator

## Version 0.15.0

- Added ability to pass custom `scope_class` to `init_dependencies` and `shutdown_dependencies`
- Added `ContextVarScope` for storing dependencies in `contextvars`
- Renamed `_internal` module to `support`
- Breaking changes:
  - Removed `ParentCallScope`
  - Renamed `enter_decorator` and `exit_decorator` to `enter_inject` and `exit_inject`
  - Renamed `LocalScope` and `GlobalScope` to `AutoScope` and `ManualScope`
  - `Scope` now can't be imported, instead use `AutoScope` or `ManualScope`
  - Replaced `Scope.close_local` and `Scope.close_global` with `[AutoScope | ManualScope].enter` and `[AutoScope | ManualScope].shutdown`

## Version 0.14.0

- Added `helpers.lifespan` function for simple resource management

## Version 0.13.0

- Fix async singleton through sync resolving

## Version 0.12.0

- `@inject` now can be placed on bottom with `@contxtlib.asyncontextmanager`
- Fix scopes closing when injecting in generator functions
- Fix scopes closing in dependencies

## Version 0.11.0

- Removed dead code branches
- Refactor injection logic
- Fix problems with generators
- Register dependencies in `inject`, not in `Provide`
- Get rid of `in_use` parameter in `Provider`

## Version 0.10.0

- Backward incompatible changes
  - Renamed `init_resources` and `shutdown_resources` to `init_dependencies` and `shutdown_dependencies`
  - Removed `resource` decorator (use `dependency` decorator with `SingletonScope` instead)
- Expose scopes to public API

## Version 0.9.0

- Experimental release (all changes are under the hood, there is no public API yet)
  - Add `dependency` decorator, now you can specify scope_class, even user-defined
  - Add `ParentCallScope` - dependency result cached for lifetime of parent function call

## Version 0.8.0

- Clear store for singleton scope on `shutdown_resource`

## Version 0.7.1

- Fix "coroutine was never awaited" warning when closing context manager for sync function in async context

## Version 0.7.0

- Added `registry` object for managing dependencies
- Now you can override dependencies. Useful for testing and "ABC" dependencies
- Removed `make_dependency` experimental function
- Some code cleanups
- Fixed tests inconsistency (cleanup picodi resources after each test)

## Version 0.6.0

- Add `helpers` module
- Fix potential `RuntimeWarning`

## Version 0.5.0

- Switch from storing only resource deps to storing all deps
- Don't initialize unused resources
- Refactor scope resource management
- Removed dead code (detecting fastapi dependency)

## Version 0.4.3

- Fix resource placement bug
- Change typings for `init_resources` and `shutdown_resources`. Now they always return `Awaitable`.
- Add tests for FastAPI integration

## Version 0.4.2

- Fix injected generator dependencies resolving

## Version 0.4.1

- Fix FastAPI support

## Version 0.4.0

- Added `make_dependency` function (experimental)

## Version 0.3.0

- Internal refactoring
- Updated README.md

## Version 0.2.0

- Removed `use_cache` parameter
- Added tests

## Version 0.1.1

- Fix context manager error

## Version 0.1.0

- Initial release
