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
and offers features like resource lifecycle management.

## Table of Contents

- [Status](#status)
- [Installation](#installation)
- [Features](#features)
- [Quick Start](#quick-start)
- [Basic Usage](#basic-usage)
  - [Declaring dependencies](#declaring-dependencies)
  - [Injecting dependencies](#injecting-dependencies)
  - [Declaring dependencies that acts like a context manager](#declaring-dependencies-that-acts-like-a-context-manager)
  - [Declaring resource dependencies](#declaring-resource-dependencies)
  - [Resolving async dependencies in sync functions](#resolving-async-dependencies-in-sync-functions)
  - [Overriding dependencies](#overriding-dependencies)
  - [Using picodi with web frameworks](#using-picodi-with-web-frameworks)
  - [Helper functions](#helper-functions)
- [Known Issues](#known-issues)
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
- 🔄 Resource lifecycle management
- 🔍 Type hints support
- 🐍 Python & PyPy 3.10+ support

## Quick Start

```python
import asyncio
from collections.abc import Callable
from datetime import date
from typing import Any

import httpx

from picodi import Provide, init_dependencies, inject, resource, shutdown_dependencies
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


# We want to reuse the same client for all requests, so we create a resource that
#   provides an httpx.AsyncClient instance with the correct settings.
@resource
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
    # Initialize resources on the application startup. This will create the
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

    # Closing all inited resources. This needs to be done on the application shutdown.
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

### Declaring dependencies that acts like a context manager

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

`get_db` and `process_data` also can be async, just add `async` keyword before `def`.

### Declaring resource dependencies

Use the `resource` decorator to declare a resource,
which ensures that the provided function is treated as a singleton
and that its lifecycle is managed across the application.

```python
import asyncio
import random

from picodi import Provide, inject, resource, shutdown_dependencies


# useful for managing resources like connections
@resource
async def get_db_port():
    yield random.randint(1024, 49151)
    print("closing db port")


@inject
async def check_port(port: int = Provide(get_db_port)) -> None:
    print("checking port:", port)


async def main() -> None:
    await check_port()
    await check_port()
    print("shutting down resources")
    # resources need to be closed manually
    await shutdown_dependencies()


asyncio.run(main())
# -> checking port: 24090
# -> checking port: 24090
# -> shutting down resources
# -> closing db port
```

### Resolving async dependencies in sync functions

Attempting to resolve async dependencies in sync functions may not work as expected,
resulting in unexpected behaviors like receiving a coroutine object instead of the actual value.

```python
async def get_db_port() -> int:
    return 8080


@inject
def print_port(port: int = Provide(get_db_port)) -> None:
    print("port is:", port)
    # port is: <coroutine object get_db_port at 0x1037741a0>
```

But if your dependency is a resource,
you can use `init_dependencies` on startup to resolve dependencies and then use cached values,
even in sync functions.
But regular async functions will still need to be used only in async context.

```python
from picodi import Provide, init_dependencies, inject, resource

@resource
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

from my_app.dependencies import get_settings


def get_test_settings():
    return {"test": "settings"}


@pytest.fixture()
def _settings():
    with registry.override(get_settings, get_test_settings):
        yield  # use yield, so the override will be cleared after the test
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

For clearing specific override, you can pass None as a new dependency.

```python
from picodi import registry


registry.override(get_abc_setting, None)
```

For clearing all overrides you can use `registry.clear_overrides()`.

```python
from picodi import registry


registry.clear_overrides()
```

### Using picodi with web frameworks

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

### Helper functions

#### `helpers.get_value`

Function to get a value from a nested dictionary or object.
Can be useful for getting single value from settings object
and not be dependent on the type of the object.

```python
from picodi import inject, Provide
from picodi.helpers import get_value

def get_settings():
    return {
        "db": {
            "host": "localhost",
            "port": 8000
        }
    }


@inject
def get_setting(path: str, settings: dict = Provide(get_settings)):
    value = get_value(path, settings)
    return lambda: value


@inject
def get_connection(
    host: str = Provide(get_setting(path="db.host")),
    port: int = Provide(get_setting(path="db.port")),
):
    print("connecting to", host, port)
    # -> connecting to localhost 8000
```

## Known Issues

### I'm getting a coroutine object instead of the actual value

If you are trying to resolve async dependencies in sync functions, you will get a coroutine object.
For regular dependencies this is intended behavior, so only use async dependencies in async functions.
But if your dependency is a resource, you can use `init_dependencies` on app startup to resolve dependencies
and then picodi will use cached values, even in sync functions.

### Resources are not initialized when i call `init_dependencies()`

1. If you have async dependencies - make sure that you are calling `await init_dependencies()` in async context.
2. Make sure that modules with your `@resource` functions are imported (e.g. registered) before calling `init_dependencies()`.

### flake8-bugbear throws `B008 Do not perform function calls in argument defaults.

Edit `extend-immutable-calls` in your `setup.cfg`:

`extend-immutable-calls = picodi.Provide,Provide`

### I'm getting `RuntimeError: Event loop is closed` when using pytest-asyncio

This error occurs because pytest-asyncio closes the event loop after the test is finished
and you are using `@resource` decorator for your dependencies.

To fix this, you need to close all resources after the test is finished.
Just add `await shutdown_dependencies()` at the end of your tests.

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

### `resource(fn)`

Decorator to declare a resource,
which ensures that the provided function is treated as a singleton
and that its lifecycle is managed across the application.

Should be placed first in the decorator chain (on top).

- **Parameters**:
  - `fn`: A generator function that yields a resource.

### `init_dependencies()`

Initializes all declared resources. Typically called at the startup of the application.

Can be called as `init_dependencies()` in sync context and `await init_dependencies()` in async context.

### `shutdown_dependencies()`

Cleans up all resources.
It should be called when the application is shutting down to ensure proper resource cleanup.

Can be called as `shutdown_dependencies()` in sync context and `await shutdown_dependencies()` in async context.

### `registry` object

Registry object to manage dependencies and resources.

#### `registry.override(dependency, new_dependency)`

Overrides a dependency with a new one. It can be used as a decorator, context manager
or a regular method call. The new dependency will be used instead of the old one.
Useful for testing or changing dependencies at runtime.

- **Parameters**:
  - `dependency`: The dependency to override.
  - `new_dependency`: The new dependency to use instead of the old one. Don't specify
  this parameter when using as a decorator. When passing `None`, the original dependency
  will be restored.

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

Clears all dependencies and resources. This method will not close any resources.
So you need to manually call `shutdown_dependencies` before this method.

Don't use this method in production code (only if you know what you are doing),
it's mostly for testing purposes.

### `helpers` module

Module with helper functions for working with dependencies.

#### `helpers.get_value(path, obj, default)`

Function to get a value from a nested dictionary or object.
Can deal with dictionary keys as well as object attributes.

- **Parameters**:
  - `path`: A string with keys separated by dots.
  - `obj`: A dictionary or object from which to get the value.
  - `default`: A default value to return if the key is not found.

## License

[MIT](https://github.com/yakimka/picodi/blob/main/LICENSE)


## Credits

This project was generated with [`yakimka/cookiecutter-pyproject`](https://github.com/yakimka/cookiecutter-pyproject).
