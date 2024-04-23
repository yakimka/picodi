# nanodi

[![Build Status](https://github.com/yakimka/nanodi/actions/workflows/workflow-ci.yml/badge.svg?branch=main&event=push)](https://github.com/yakimka/nanodi/actions/workflows/workflow-ci.yml)
[![Codecov](https://codecov.io/gh/yakimka/nanodi/branch/main/graph/badge.svg)](https://codecov.io/gh/yakimka/nanodi)
[![PyPI - Version](https://img.shields.io/pypi/v/nanodi.svg)](https://pypi.org/project/nanodi/)
![PyPI - Downloads](https://img.shields.io/pypi/dm/nanodi)

Simple Dependency Injection for Python

Experimental dependency injection library for Python. Use it at your own risk.

## Installation

```bash
pip install nanodi
```

## Example

```python
from nanodi import inject, Provide


def get_redis() -> str:
    yield "redis"
    print("closing redis")


@inject
def get_storage_service(redis: str = Provide(get_redis)) -> str:
    return f"storage_service({redis})"


assert get_storage_service() == "storage_service(redis)"
```

## License

[MIT](https://github.com/yakimka/nanodi/blob/main/LICENSE)


## Credits

This project was generated with [`yakimka/cookiecutter-pyproject`](https://github.com/yakimka/cookiecutter-pyproject).
