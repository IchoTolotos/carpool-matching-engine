.PHONY: audit benchmark build check format lint test type-check

format:
	python -m ruff format .
	python -m ruff check --fix .

lint:
	python -m ruff format --check .
	python -m ruff check .

type-check:
	python -m mypy

test:
	python -m pytest

build:
	python -m build

audit:
	python -m pip_audit

benchmark:
	python -m benchmarks.run

check: lint type-check test build
