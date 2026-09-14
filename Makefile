.PHONY: checks checks-all test notebook book slides

checks:
	uv run pre-commit run --all-files

checks-all:
	uv run ruff check --fix src tests notebooks
	uv run ruff format src tests notebooks

test:
	uv run pytest

notebook:
	uv run jupytext --set-formats ipynb,py:percent notebooks/overview.py

# the chapters depend on the package code, which quarto freeze does not track
book:
	rm -rf book/_freeze
	uv run python -m rse_survey_report.book
	uv run quarto render book

slides:
	uv run quarto render slides/survey-meeting.qmd
