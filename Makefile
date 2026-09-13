.PHONY: checks checks-all test notebook

checks:
	uv run pre-commit run --all-files

checks-all:
	uv run ruff check --fix src tests notebooks
	uv run ruff format src tests notebooks

test:
	uv run pytest

notebook:
	uv run jupytext --set-formats ipynb,py:percent notebooks/overview.py
