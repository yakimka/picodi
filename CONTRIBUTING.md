# How to contribute


## Dependencies

We use [poetry](https://github.com/python-poetry/poetry) to manage the dependencies.

To install them you would need to run `install` command:

```bash
poetry install
```

To activate your `virtualenv` run `poetry shell`.


## One magic command

Run `make checks` to run everything we have!


## Tests

We use `pytest` and `flake8` for quality control.

To run all tests:

```bash
make test
```

To run linting:

```bash
make lint
```
Keep in mind: default virtual environment folder excluded by flake8 style checking is `.venv`.
If you want to customize this parameter, you should do this in `pyproject.toml`.


## Type checks

We use `mypy` to run type checks on our code.
To use it:

```bash
make mypy
```


## Submitting your code

What are the point of this method?

1. We use protected `main` branch,
   so the only way to push your code is via pull request
2. We use issue branches: to implement a new feature or to fix a bug
   create a new branch
3. Then create a pull request to `main` branch
4. We use `git tag`s to make releases, so we can track what has changed
   since the latest release

In this method, the latest version of the app is always in the `main` branch.
