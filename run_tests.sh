#!/bin/bash

# Fail early
set -e

coverage run --branch --omit=tests/*,venv/* -m pytest -p no:cacheprovider tests
coverage report --fail-under=90 --show-missing --skip-covered

echo "--Black--"
black --diff --line-length=79 dht_node tests setup.py

echo "--Flake8--"
flake8 dht_node tests setup.py

echo "--Isort--"
isort --check-only --diff dht_node tests setup.py

echo "--Mypy--"
mypy --cache-dir=/dev/null dht_node tests

echo "--Pylint--"
pylint --score=no dht_node tests setup.py