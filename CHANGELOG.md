# Version history

We follow [Semantic Versions](https://semver.org/).


## Version 0.1.0

- Initial release

## Version 0.1.1

- Fix context manager error

## Version 0.2.0

- Removed `use_cache` parameter
- Added tests

## Version 0.3.0

- Internal refactoring
- Updated README.md

## Version 0.4.0

- Added `make_dependency` function (experimental)

## Version 0.4.1

- Fix FastAPI support

## Version 0.4.2

- Fix injected generator dependencies resolving

## Version 0.4.3

- Fix resource placement bug
- Change typings for `init_resources` and `shutdown_resources`. Now they always return `Awaitable`.
- Add tests for FastAPI integration

## Version 0.5.0

- Switch from storing only resource deps to storing all deps
- Don't initialize unused resources
- Refactor scope resource management
- Removed dead code (detecting fastapi dependency)

## Version 0.6.0

- Add `helpers` module
- Fix potential `RuntimeWarning`
