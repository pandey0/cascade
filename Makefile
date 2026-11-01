.PHONY: check lint type test exp0 audit openapi
check: lint type test
lint:
	ruff check src tests scripts examples && ruff format --check src tests scripts examples
type:
	mypy
test:
	pytest --cov --cov-report=term-missing
exp0:
	cascade exp0
audit:
	pip-audit
openapi:
	python scripts/export_openapi.py
