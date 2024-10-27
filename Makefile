SHELL:=/usr/bin/env bash

RUN=

.PHONY: all
all: help

.PHONY: pre-commit
pre-commit:  ## Run pre-commit with args
	$(RUN) poetry run pre-commit $(args)

.PHONY: poetry
poetry:  ## Run poetry with args
	$(RUN) poetry $(args)

.PHONY: lint
lint:  ## Run flake8, mypy, other linters and verify formatting
	@make pre-commit args="run --all-files"; \
	RESULT1=$$?; \
	make mypy; \
	RESULT2=$$?; \
	exit $$((RESULT1 + RESULT2))

.PHONY: mypy
mypy:  ## Run mypy
	$(RUN) poetry run mypy $(args)

.PHONY: test
test:  ## Run tests
	$(RUN) poetry run pytest --cov=tests --cov=picodi $(args)
	$(RUN) poetry run pytest --dead-fixtures

benchmark:  ## Run benchmark
	$(RUN) poetry run pytest --run-benchmarks $(args)

benchmark-compare:  ## Run benchmark
	$(RUN) poetry run pytest --run-benchmarks --benchmark-compare --benchmark-compare-fail=mean:10% $(args)

.PHONY: test-docs
test-docs:  ## Check docs
	$(MAKE) -C docs test
	$(RUN) poetry run pytest --markdown-docs -m markdown-docs $(args)

.PHONY: package
package:  ## Run packages (dependencies) checks
	$(RUN) poetry check
	$(RUN) poetry run pip check

.PHONY: build-package
build-package:  ## Build package
	$(RUN) poetry build $(args)
	$(RUN) poetry export --format=requirements.txt --output=dist/requirements.txt

.PHONY: checks
checks: lint package test  ## Run linting and tests

.PHONY: run-ci
run-ci:  ## Run CI locally
	$(RUN) ./ci.sh

.PHONY: clean
clean:  ## Clean up
	rm -rf dist
	rm -rf htmlcov
	rm -f .coverage coverage.xml
	$(MAKE) -C docs clean

.PHONY: clean-all
clean-all:  ## Clean up all
	@make clean
	rm -rf .cache
	rm -rf .mypy_cache
	rm -rf .pytest_cache

.PHONY: docs
docs:
	$(MAKE) -C docs html

.PHONY: help
help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
