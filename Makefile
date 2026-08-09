.PHONY: audit benchmark benchmark-scale build check example format lint test type-check

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

benchmark-scale:
	python -m benchmarks.scale --repetitions 5 --seconds-per-run 1

example:
	python examples/basic.py

check: lint type-check test build
