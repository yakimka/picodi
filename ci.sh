#!/usr/bin/env bash

set -o errexit
set -o nounset
set -o pipefail

# Initializing global variables and functions:
: "${CI:=0}"

pyclean () {
  echo 'cleaning up...'
}

run_ci () {
  echo '[ci started]'
  set -x  # we want to print commands during the CI process.

  # Testing filesystem and permissions:
  touch .perm && rm -f .perm

  uv sync
  uv run pre-commit run --all-files
  uv run mypy
  uv check
  uv run pip check
  uv run pytest --cov=tests --cov=picodi --cov-report=xml --junitxml=jcoverage.xml
  uv run pytest --dead-fixtures
  uv build
  uv export --format=requirements-txt --output-file=dist/requirements.txt --locked --no-dev --no-emit-project
  # print shasum of the built packages
  shasum dist/*
  # trying to build the docs
  (cd docs && make html && make test)

  set +x
  echo '[ci finished]'
}

# Remove any cache before the script:
pyclean

# Clean everything up:
trap pyclean EXIT INT TERM

# Run the CI process:
run_ci
