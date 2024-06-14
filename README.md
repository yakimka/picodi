# Picodi - Python DI (Dependency Injection) Library

[![Build Status](https://github.com/yakimka/picodi/actions/workflows/workflow-ci.yml/badge.svg?branch=main&event=push)](https://github.com/yakimka/picodi/actions/workflows/workflow-ci.yml)
[![Codecov](https://codecov.io/gh/yakimka/picodi/branch/main/graph/badge.svg)](https://codecov.io/gh/yakimka/picodi)
[![PyPI - Version](https://img.shields.io/pypi/v/picodi.svg)](https://pypi.org/project/picodi/)
![PyPI - Downloads](https://img.shields.io/pypi/dm/picodi)

Picodi simplifies Dependency Injection (DI) for Python applications.
[DI](https://en.wikipedia.org/wiki/Dependency_injection) is a design pattern
that allows objects to receive their dependencies from
an external source rather than creating them internally.
This library supports both synchronous and asynchronous contexts,
and offers features like lifecycle management.

## Table of Contents

- [Status](#status)
- [Installation](#installation)
- [Features](#features)
- [Quick Start](#quick-start)
- [Basic Usage](#basic-usage)
  - [Declaring dependencies](#declaring-dependencies)
  - [Injecting dependencies](#injecting-dependencies)
  - [Declaring dependencies that act as context managers](#declaring-dependencies-that-act-as-context-managers)
- [Advanced Usage](#advanced-usage)
  - [Scopes](#scopes)
    - [NullScope](#nullscope)
    - [SingletonScope](#singletonscope)
    - [ParentCallScope](#parentcallscope)
    - [Defining custom scopes](#defining-custom-scopes)
  - [Resolving async dependencies in sync functions](#resolving-async-dependencies-in-sync-functions)
  - [Overriding dependencies](#overriding-dependencies)
  - [Using Picodi with web frameworks](#using-picodi-with-web-frameworks)
- [Known Issues](#known-issues)
  - [Receiving a coroutine object instead of the actual value](#receiving-a-coroutine-object-instead-of-the-actual-value)
  - [Global scoped dependencies not initialized with `init_dependencies()`](#global-scoped-dependencies-not-initialized-with-init_dependencies)
  - [flake8-bugbear throws `B008 Do not perform function calls in argument defaults`](#flake8-bugbear-throws-b008-do-not-perform-function-calls-in-argument-defaults)
  - [RuntimeError: Event loop is closed when using pytest-asyncio](#runtimeerror-event-loop-is-closed-when-using-pytest-asyncio)
- [API Reference](#api-reference)
- [License](#license)
- [Credits](#credits)

## Status

Picodi is currently in the experimental stage.
Public APIs may change without notice until the library reaches a 1.x.x version.

## Installation

```bash
pip install picodi
```

## Features

- 🌟 Simple and lightweight
- 📦 Zero dependencies
- ⏱️ Supports both sync and async contexts
- 🔄 Lifecycle management
- 🔍 Type hints support
- 🐍 Python & PyPy 3.10+ support

## Quick Start

```python
import asyncio
from collections.abc import Callable
from datetime import date
from typing import Any

import httpx

from picodi import Provide, init_dependencies, inject, dependency, SingletonScope, shutdown_dependencies
from picodi.helpers import get_value


# Regular functions without required arguments can be used as a dependency
def get_settings() -> dict:
    return {
        "nasa_api": {
            "api_key": "DEMO_KEY",
            "base_url": "https://api.nasa.gov",
            "timeout": 10,
        }
    }


# Helper function to get a setting from the settings dictionary.
# We can use this function to inject specific settings, not the whole settings object.
@inject
def get_setting(path: str, settings: dict = Provide(get_settings)) -> Callable[[], Any]:
    value = get_value(path, settings)
    return lambda: value


# We want to reuse the same client for all requests, so we declare a dependency
#   with `SingletonScope` that provides an httpx.AsyncClient instance
#   with the correct settings.
@dependency(scope_class=SingletonScope)
@inject
async def get_nasa_client(
    api_key: str = Provide(get_setting("nasa_api.api_key")),
    base_url: str = Provide(get_setting("nasa_api.base_url")),
    timeout: int = Provide(get_setting("nasa_api.timeout")),
) -> httpx.AsyncClient:
    async with httpx.AsyncClient(
        base_url=base_url, params={"api_key": api_key}, timeout=timeout
    ) as client:
        yield client


@inject
async def get_apod(
    date: date, client: httpx.AsyncClient = Provide(get_nasa_client)
) -> dict[str, Any]:
    # Printing the client ID to show that the same client is reused for all requests.
    print("Client ID:", id(client))
    response = await client.get("/planetary/apod", params={"date": date.isoformat()})
    response.raise_for_status()
    return response.json()


@inject
# Note that asynchronous `get_nasa_client` is injected
#  in synchronous `print_client_info` function.
def print_client_info(client: httpx.AsyncClient = Provide(get_nasa_client)):
    print("Client ID:", id(client))
    print("Client Base URL:", client.base_url)
    print("Client Params:", client.params)
    print("Client Timeout:", client.timeout)


async def main():
    # Initialize dependencies on the application startup. This will create the
    #   httpx.AsyncClient instance and cache it for later use. Thereby, the same
    #   client will be reused for all requests. This is important for connection
    #   pooling and performance.
    # Also `init_dependencies` call will allow to pass asynchronous `get_nasa_client`
    #   into synchronous functions.
    await init_dependencies()

    print_client_info()

    apod_data = await get_apod(date(2011, 7, 19))
    print("Title:", apod_data["title"])

    apod_data = await get_apod(date(2011, 7, 26))
    print("Title:", apod_data["title"])

    # Closing all inited dependencies. This needs to be done on the application shutdown.
    await shutdown_dependencies()


if __name__ == "__main__":
    asyncio.run(main())
# Client ID: 4334576784
# Client Base URL: https://api.nasa.gov
# Client Params: api_key=DEMO_KEY
# Client Timeout: Timeout(timeout=10)
#
# Client ID: 4334576784
# Title: Vesta Vista
#
# Client ID: 4334576784
# Title: Galaxy NGC 474: Cosmic Blender
```
## Basic Usage

Picodi uses decorators, functions and generators to provide and inject dependencies.

### Declaring dependencies

Dependencies can be simple functions or generators that act as context managers.

```python
# A simple function returning a static number,
#   and this function can be used as a dependency
def get_meaning_of_life():
    return 42


# A generator to manage database connections, cleaning up after usage
def get_meaning_of_life():
    print("setup")
    yield 42
    print("teardown")


# Or async version
async def get_meaning_of_life():
    print("setup")
    yield 42
    print("teardown")
```

### Injecting dependencies

Declare dependencies in function arguments using the `Provide` function.
Use the `inject` decorator to automatically inject dependencies into a function.

```python
from picodi import inject, Provide


def get_db_port() -> int:
    return 8000


@inject
def get_connection_settings(port: int = Provide(get_db_port)):
    return {"port": port}
```

### Declaring dependencies that act as context managers

You can use a generator to declare dependencies that need to be cleaned up after use.

```python
from picodi import Provide, inject


def get_db():
    yield "db connection"
    print("closing db connection")


@inject
def process_data(db: str = Provide(get_db)) -> None:
    print("processing data in db:", db)
```

`get_db` and `process_data` can also be async by adding the `async` keyword before `def`.

## Advanced Usage

### Scopes

Scopes define the lifecycle of a dependency.
Picodi provides three scopes: `NullScope`, `SingletonScope`, and `ParentCallScope`.
You can create your own scopes by inheriting from the `LocalScope` or `GlobalScope` class.

Use the `dependency` decorator to specify the scope of a dependency.

```python
import random

from picodi import dependency, SingletonScope


@dependency(scope_class=SingletonScope)
async def get_db_port():
    yield random.randint(1024, 49151)
    print("closing db port")
```

#### NullScope

Default scope for dependencies.
Doesn't cache the dependency result - the dependency will be called on each injection.
Yield dependencies are closed after every call.

#### SingletonScope

Scope for dependencies that should be created once and reused for all injections.
Closes the dependency when `shutdown_dependencies` is called.

#### ParentCallScope

Scope for dependencies that should be created once per parent call.
Yield dependencies are closed after the parent function call.

Example:

```python
import random

from picodi import dependency, ParentCallScope, Provide, inject


@dependency(scope_class=ParentCallScope)
async def get_db_port():
    yield random.randint(1024, 49151)
    print("closing db port")


@inject
async def get_a(port: int = Provide(get_db_port)):
    print("A port:", port)
    return port


@inject
async def get_b(port: int = Provide(get_db_port)):
    print("B port:", port)
    return port


@inject
async def parent_call(a: int = Provide(get_a), b: int = Provide(get_b)):
    # a == b because they are called in the same parent function
    # "closing db port" will be printed only once after `parent_call` call
    print("parent call", a, b)
```

#### Defining custom scopes

You can define custom scopes by inheriting from the `LocalScope` or `GlobalScope` class
and implementing the required methods.

Inherit from `GlobalScope` to manage dependencies that should be created once and reused for all injections.
Otherwise, inherit from `LocalScope` to manage dependencies that should be created once per injection.

### Resolving async dependencies in sync functions

Attempting to resolve async dependencies in sync functions may not work as expected,
resulting in unexpected behaviors like receiving a coroutine object instead of the actual value.

```python
from picodi import Provide, inject


async def get_db_port() -> int:
    return 8080


@inject
def print_port(port: int = Provide(get_db_port)) -> None:
    print("port is:", port)
    # -> port is: <coroutine object get_db_port at 0x1037741a0>
```

However, if your dependency is declared with a `GlobalScope` like `SingletonScope`,
you can use `init_dependencies` on startup to resolve dependencies and then use cached values,
even in sync functions.
Regular async functions will still need to be used only in async contexts.

```python
from picodi import Provide, init_dependencies, inject, dependency, SingletonScope

@dependency(scope_class=SingletonScope)
async def get_db_port():
    yield 8080


@inject
def print_port(port: int = Provide(get_db_port)) -> None:
    print("port is:", port)
    # -> port is: 8080


async def main() -> None:
    await init_dependencies()
    print_port()
```

### Overriding dependencies

You can override dependencies at runtime. This is important for testing and useful
for implementing "abstract" dependencies.

```python
import pytest

from picodi import registry


# Dependency that return app settings
#   usually it should be implemented in the app
def get_settings():
    ...


def get_test_settings():
    return {"test": "settings"}


@pytest.fixture()
def _settings():
    with registry.override(get_settings, get_test_settings):
        # use yield, so the override will be cleared after each test
        yield
```

"Abstract" dependencies can be used to provide a default implementation for a dependency,
which can be overridden at runtime. This is useful for reusing dependencies in different contexts.

```python
from picodi import Provide, inject, registry


def get_abc_setting() -> dict:
    raise NotImplementedError


@inject
def my_service(settings: dict = Provide(get_abc_setting)) -> dict:
    return settings


@registry.override(get_abc_setting)
def get_setting():
    return {"my": "settings"}


print(my_service())  # -> {'my': 'settings'}
```

You can also use `registry.override` as a regular method call.

```python
from picodi import registry


def get_abc_setting() -> dict:
    raise NotImplementedError


def get_setting():
    return {"my": "settings"}


registry.override(get_abc_setting, get_setting)
```

To clear a specific override, you can pass None as the new dependency.

```python continuation
from picodi import registry


registry.override(get_abc_setting, None)
```

To clear all overrides, you can use `registry.clear_overrides()`.

```python
from picodi import registry


registry.clear_overrides()
```

### Using Picodi with web frameworks

Picodi can be used with web frameworks like FastAPI or Django.

```python
import random

from fastapi import FastAPI, Depends
from picodi import Provide, inject

app = FastAPI()


def get_random_int():
    yield random.randint(1, 100)


@inject
async def get_redis_connection(port: int = Provide(get_random_int)) -> str:
    return "http://redis:{}".format(port)


@app.get("/")
@inject
async def read_root(redis: str = Depends(Provide(get_redis_connection))):
    return {"redis": redis}


# uvicorn fastapi_di:app --reload
```

## Known Issues

### Receiving a coroutine object instead of the actual value

If you are trying to resolve async dependencies in sync functions, you will receive a coroutine object.
For regular dependencies, this is intended behavior, so only use async dependencies in async functions.
However, if your dependency uses a scope inherited from `GlobalScope`,
you can use `init_dependencies` on app startup to resolve dependencies,
and then Picodi will use cached values, even in sync functions.

### Global scoped dependencies not initialized with `init_dependencies()`

1. If you have async dependencies, ensure that you are calling `await init_dependencies()` in an async context.
2. Ensure that modules with your global scoped functions are imported (e.g., registered) before calling `init_dependencies()`.

### flake8-bugbear throws `B008 Do not perform function calls in argument defaults`

Edit `extend-immutable-calls` in your `setup.cfg`:

`extend-immutable-calls = picodi.Provide,Provide`

### RuntimeError: Event loop is closed when using pytest-asyncio

This error occurs because pytest-asyncio closes the event loop after the test finishes
and you are using global scoped dependencies.

To fix this, you need to close all resources after the test finishes.
Add `await shutdown_dependencies()` at the end of your tests.

```python
import picodi
import pytest


@pytest.fixture(autouse=True)
async def _setup_picodi():
    yield
    await picodi.shutdown_dependencies()
```

## API Reference

### `Provide(dependency)`

Marks a callable as a provider of a dependency.

- **Parameters**:
  - `dependency`: A callable that returns the dependency or a generator for context management.

### `inject(fn)`

Decorator to automatically inject dependencies declared by `Provide` into a function.
It manages the lifecycle of the dependency,
including initialization and teardown if the dependency is a generator.

Should be placed first in the decorator chain (on bottom).

- **Parameters**:
  - `fn`: The function into which dependencies will be injected.

### `dependency(*, scope_class)`

Decorator to declare a dependency with a specific scope.

Should be placed first in the decorator chain (on top).

- **Parameters**:
  - `scope_class`: A class that defines the scope of the dependency.
    Available scopes are `NullScope` (default), `SingletonScope`, and `ParentCallScope`.

### `Scope` class

Base class for defining dependency scopes.

#### `Scope.get(key)`

Get a dependency by key. Key is a dependency function.
If the value does not exist, it must raise KeyError.

#### `Scope.set(key, value)`

Set a dependency by key. Key is a dependency function.

#### `Scope.close_local()`

Hook for closing dependencies. Will be called automatically
after executing a decorated function.

#### `Scope.close_global()`

Hook for closing dependencies. Will be called from `shutdown_dependencies`.

#### `Scope.enter_decorator()`

Called when entering an `inject` decorator for dependencies with this scope.
With `Scope.exit_decorator()`, it can be used for tracking decorator nesting.

#### `Scope.exit_decorator()`

Called when exiting an `inject` decorator for dependencies with this scope.

### `LocalScope` class

Base class for defining local dependency scopes. A local dependency scope
calls `close_local` after each function call.

### `GlobalScope` class

Base class for defining global dependency scopes. A global dependency scope
calls `close_global` from the `shutdown_dependencies` function.

Global scoped dependencies can be managed by `init_dependencies` and `shutdown_dependencies`.

### `NullScope` class

Default scope for dependencies. Doesn't cache the dependency result -
the dependency will be called on each injection. Yield dependencies are closed after every call.

### `SingletonScope` class

Scope for dependencies that should be created once and reused for all injections.
Closes the dependency when `shutdown_dependencies` is called.
Useful for managing resources like connections.

### `ParentCallScope` class

Scope for dependencies that should be created once per parent call.
Yield dependencies are closed after the parent function call.

### `init_dependencies()`

Initializes all global scoped dependencies. Typically called at the startup of the application.

Can be called as `init_dependencies()` in a sync context and `await init_dependencies()` in an async context.

### `shutdown_dependencies()`

Calls all dependency teardowns.
It should be called when the application is shutting down to ensure proper cleanup.

Can be called as `shutdown_dependencies()` in a sync context and `await shutdown_dependencies()` in an async context.

### `registry` object

Registry object to manage dependencies.

#### `registry.override(dependency, new_dependency)`

Overrides a dependency with a new one. It can be used as a decorator, context manager,
or a regular method call. The new dependency will be used instead of the old one.
Useful for testing or changing dependencies at runtime.

- **Parameters**:
  - `dependency`: The dependency to override.
  - `new_dependency`: The new dependency to use instead of the old one. Don't specify
  this parameter when using it as a decorator. When passing `None`, the original dependency
  will be restored.

Example:

```python
from picodi import registry

def get_settings():
    raise NotImplementedError


# as a decorator
@registry.override(get_settings)
def real_settings():
    return {"real": "settings"}


# as a context manager
with registry.override(get_settings, real_settings):
    ...

# as a regular method call
registry.override(get_settings, real_settings)
registry.override(get_settings, None)  # clear override
```

#### `registry.clear_overrides()`

Clears all overrides set by `registry.override()`.

#### `registry.clear()`

Clears all dependencies. This method will not close any context managers.
You need to manually call `shutdown_dependencies` before this method.

Don't use this method in production code (only if you know what you are doing),
as it's mostly for testing purposes.

### `helpers` module

Module with helper functions for working with dependencies.

#### `helpers.get_value(path, obj, default)`

Function to get a value from a nested dictionary or object.
Can deal with dictionary keys as well as object attributes.

- **Parameters**:
  - `path`: A string with keys separated by dots.
  - `obj`: A dictionary or object from which to get the value.
  - `default`: A default value to return if the key is not found.

Example:

```python
from picodi import inject, Provide
from picodi.helpers import get_value


settings = {
    "db": {
        "host": "localhost",
        "port": 5432,
    }
}


def get_setting(path: str):
    value = get_value(path, settings)
    return lambda: value


@inject
def get_connection(
    host: str = Provide(get_setting(path="db.host")),
    port: int = Provide(get_setting(path="db.port")),
):
    print("connecting to", host, port)
```

#### `helpers.lifespan(fn=None)`

Decorator and context manager to manage the lifecycle of a dependencies.
This is equivalent of:

```python
import picodi


picodi.init_dependencies()
# your code
picodi.shutdown_dependencies()
```

Can be used as a decorator:

```python
from picodi.helpers import lifespan


@lifespan
def main():
    # Depedencies will be initialized before this function call
    # and closed after this function call
    ...

# or for async functions
@lifespan
async def async_main():
    ...
```

Can be used as a context manager:

```python
from picodi.helpers import lifespan


with lifespan():  # or `async with lifespan():` for async functions
    ...
```

`lifespan` can automatically detect if the function is async or not.
But if you want to force sync or async mode,
you can use `lifespan.sync` or `lifespan.async_`:

```python
from picodi.helpers import lifespan


with lifespan.sync():
    ...


@lifespan.async_()
async def main():
    ...
```

## License

[MIT](https://github.com/yakimka/picodi/blob/main/LICENSE)


## Credits

This project was generated with [`yakimka/cookiecutter-pyproject`](https://github.com/yakimka/cookiecutter-pyproject).
