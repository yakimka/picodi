# Picodi - Python DI (Dependency Injection) Library

[![Build Status](https://github.com/yakimka/picodi/actions/workflows/workflow-ci.yml/badge.svg?branch=main&event=push)](https://github.com/yakimka/picodi/actions/workflows/workflow-ci.yml)
[![Codecov](https://codecov.io/gh/yakimka/picodi/branch/main/graph/badge.svg)](https://codecov.io/gh/yakimka/picodi)
[![PyPI - Version](https://img.shields.io/pypi/v/picodi.svg)](https://pypi.org/project/picodi/)
[![PyPI - Python Version](https://img.shields.io/pypi/pyversions/picodi)](https://pypi.org/project/picodi/)
[![PyPI - Downloads](https://img.shields.io/pypi/dm/picodi)](https://pypi.org/project/picodi/)
[![Documentation Status](https://readthedocs.org/projects/picodi/badge/?version=stable)](https://picodi.readthedocs.io/en/stable/?badge=stable)

[Documentation](https://picodi.readthedocs.io/)

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
- [FastAPI Example Project](#fastapi-example-project)
- [License](#license)
- [Contributing](#contributing)
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
- 🚀 Works well with [FastAPI](https://fastapi.tiangolo.com/)
- 🧪 Integration with [pytest](https://docs.pytest.org/)

## Quick Start

```python
import asyncio
from collections.abc import Callable
from datetime import date
from typing import Any

import httpx

from picodi import (
    Provide,
    inject,
    registry,
    SingletonScope,
)
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
@registry.set_scope(
    scope_class=SingletonScope,
    auto_init=True,
)
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


# `lifespan` will initialize dependencies on the application startup.
#   This will create the
#   httpx.AsyncClient instance and cache it for later use. Thereby, the same
#   client will be reused for all requests. This is important for connection
#   pooling and performance. Because it's created on app startup,
#   it will allow to pass asynchronous `get_nasa_client` into synchronous functions.
# And closing all inited dependencies after the function execution.
@registry.alifespan()
async def main():
    print_client_info()

    apod_data = await get_apod(date(2011, 7, 19))
    print("Title:", apod_data["title"])

    apod_data = await get_apod(date(2011, 7, 26))
    print("Title:", apod_data["title"])


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

## FastAPI Example Project

Here is an example of a FastAPI application
that uses Picodi for dependency injection:

[Picodi FastAPI Example](https://github.com/yakimka/picodi-fastapi-example)

## License

[MIT](https://github.com/yakimka/picodi/blob/main/LICENSE)

## Contributing

Contributions are welcome!
Please read the [CONTRIBUTING.md](https://github.com/yakimka/picodi/blob/main/CONTRIBUTING.md) file for more information.

## Credits

This project was generated with [`yakimka/cookiecutter-pyproject`](https://github.com/yakimka/cookiecutter-pyproject).
