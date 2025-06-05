#!/bin/bash

# Script to check code formatting with ruff
# Usage: ./scripts/ruff_format_check.sh

set -e

# Check if ruff is installed
if ! command -v ruff &> /dev/null
then
    echo "Ruff is not installed. Installing it now..."
    pip install ruff
fi

echo "Checking code formatting with ruff..."
ruff format .

echo "Checking code linting with ruff..."
ruff check . --fix

echo "Running pre-commit hooks..."
pre-commit run --all-files

echo "Done!"
