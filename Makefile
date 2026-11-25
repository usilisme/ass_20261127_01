.PHONY: install run test lint format typecheck check clean

install:  ## Create a virtual environment and install the package with dev tools
	python3 -m venv .venv
	.venv/bin/python -m pip install -e ".[dev]"

run:  ## Start the interactive simulation
	.venv/bin/auto-driving

test:  ## Run the test suite with coverage
	.venv/bin/pytest

lint:  ## Check style and common mistakes
	.venv/bin/ruff check .
	.venv/bin/ruff format --check .

format:  ## Auto-format the code
	.venv/bin/ruff check --fix .
	.venv/bin/ruff format .

typecheck:  ## Run the strict static type checker
	.venv/bin/mypy

check: lint typecheck test  ## Everything CI runs

clean:
	rm -rf .venv build dist *.egg-info .pytest_cache .mypy_cache .ruff_cache .coverage htmlcov
	find . -name __pycache__ -type d -prune -exec rm -rf {} +
