.PHONY: checks test

checks:
	uv run pre-commit run --all-files

checks-all:
	uv run ruff check --fix src tests

test:
	uv run pytest