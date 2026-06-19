.PHONY: install test lint format docs clean build publish

install:
	pip install -e ".[dev]"

test:
	pytest --tb=short -q

test-integration:
	pytest -m integration --tb=short -q

lint:
	ruff check .
	ruff format --check .

format:
	ruff format .
	ruff check --fix .

docs:
	mkdocs serve

docs-build:
	mkdocs build

clean:
	rm -rf dist/ build/ *.egg-info/ .pytest_cache/ .ruff_cache/
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

build:
	python -m build

publish:
	python -m twine upload dist/*
