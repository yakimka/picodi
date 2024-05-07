# Picodi - Python DI (Dependency Injection) Library

[![Build Status](https://github.com/yakimka/picodi/actions/workflows/workflow-ci.yml/badge.svg?branch=main&event=push)](https://github.com/yakimka/picodi/actions/workflows/workflow-ci.yml)
[![Codecov](https://codecov.io/gh/yakimka/picodi/branch/main/graph/badge.svg)](https://codecov.io/gh/yakimka/picodi)
[![PyPI - Version](https://img.shields.io/pypi/v/picodi.svg)](https://pypi.org/project/picodi/)
![PyPI - Downloads](https://img.shields.io/pypi/dm/picodi)

Simple Dependency Injection for Python.
This library supports both synchronous and asynchronous contexts
and offers features like resource lifecycle management.

## Status

Picodi is currently in the experimental stage.
Public APIs may change without notice until the library reaches a 1.x.x version.
Use it at your own risk.

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
- 🐍 Python 3.10+

## Basic Usage

Picodi uses decorators, functions and generators to provide and inject dependencies:

### Declaring dependencies

Dependencies can be simple functions or generators that act as context managers.

```python
import asyncio
import random


# this is a simple function that returns a random port number
#   and this function can be used as a dependency
def get_random_db_port() -> int:
    return random.randint(1024, 49151)


# or async version
async def get_random_db_port_async() -> int:
    await asyncio.sleep(1)
    return random.randint(1024, 49151)
```

### Injecting dependencies

Declare dependencies in function arguments using the `Provide` function.
Use the `inject` decorator if you want to resolve `Provide` dependencies on function call:

```python
import random

from picodi import inject, Provide


def get_random_db_port() -> int:
    return random.randint(1024, 49151)


@inject
def get_connection_settings(port: int = Provide(get_random_db_port)):
    return {"port": port}

# get_connection_settings() will return
# a dictionary with a random port number on every call
```

### Declaring dependencies that acts like a context manager

You can also use a generator to declare dependencies that need to be cleaned up after use:

```python
from typing import Generator

from picodi import Provide, inject


# also can be async, just use `async def`
def get_db() -> Generator[str, None, None]:
    yield "db connection"
    print("closing db connection")


@inject
def process_data(db: str = Provide(get_db)) -> None:
    print("processing data in db:", db)

process_data()
# -> processing data in db: db connection
# -> closing db connection
```

### Declaring resource dependencies

Use the `resource` decorator to declare a resource,
which ensures that the provided function is treated as a singleton
and that its lifecycle is managed across the application:

```python
import asyncio
import random
from typing import AsyncGenerator

from picodi import Provide, inject, resource, shutdown_resources


# useful for managing resources like connections
@resource
async def get_db_port() -> AsyncGenerator[int, None]:
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
    await shutdown_resources()


asyncio.run(main())
# -> checking port: 24090
# -> checking port: 24090
# -> shutting down resources
# -> closing db port
```

### Resolving async dependencies in sync functions

If you try to resolve async dependencies in sync functions, you may get not what you expect.

```python
import asyncio

from picodi import Provide, inject


async def get_db_port() -> int:
    return 8080


@inject
def print_port(port: int = Provide(get_db_port)) -> None:
    print("port is:", port)


async def main() -> None:
    print_port()


asyncio.run(main())
# -> port is: <coroutine object get_db_port at 0x1037741a0>
```

But if your dependency is a resource,
you can use `init_resources` on startup to resolve dependencies and then use cached values,
even in sync functions:

```python
import asyncio
from typing import AsyncGenerator

from picodi import Provide, init_resources, inject, resource

@resource
async def get_db_port() -> AsyncGenerator[int, None]:
    yield 8080


@inject
def print_port(port: int = Provide(get_db_port)) -> None:
    print("port is:", port)


async def main() -> None:
    await init_resources()
    print_port()


asyncio.run(main())
# -> port is: 8080
```

## Using picodi with web frameworks

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

## API Reference

### `Provide(dependency)`

Marks a callable as a provider of a dependency.
It manages the lifecycle of the dependency,
including initialization and teardown if the dependency is a generator.

- **Parameters**:
  - `dependency`: A callable that returns the dependency or a generator for context management.

### `inject(fn)`

Decorator to automatically inject dependencies declared by `Provide` into a function.

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

### `init_resources()`

Initializes all declared resources. Typically called at the startup of the application.

Can be called as `init_resources()` in sync context and `await init_resources()` in async context.

### `shutdown_resources()`

Cleans up all resources.
It should be called when the application is shutting down to ensure proper resource cleanup.

Can be called as `shutdown_resources()` in sync context and `await shutdown_resources()` in async context.

## License

[MIT](https://github.com/yakimka/picodi/blob/main/LICENSE)


## Credits

This project was generated with [`yakimka/cookiecutter-pyproject`](https://github.com/yakimka/cookiecutter-pyproject).
