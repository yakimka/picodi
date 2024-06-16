# Version history

We follow [Semantic Versions](https://semver.org/).

## Version next

-

## Version 0.15.0

- Added ability to pass custom `scope_class` to `init_dependencies` and `shutdown_dependencies`
- Breaking changes:
  - Removed `ParentCallScope`
  - Renamed `enter_decorator` and `exit_decorator` to `enter_inject` and `exit_inject`
  - Renamed `LocalScope` and `GlobalScope` to `AutoScope` and `ManualScope`

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
