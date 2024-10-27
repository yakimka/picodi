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

  poetry install
  poetry run pre-commit run --all-files
  poetry run mypy
  poetry check
  poetry run pip check
  poetry run pytest --cov=tests --cov=picodi --cov-report=xml --junitxml=jcoverage.xml
  poetry run pytest --dead-fixtures
  poetry run pytest --run-benchmarks --benchmark-autosave
  poetry build
  poetry export --format=requirements.txt --output=dist/requirements.txt
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
