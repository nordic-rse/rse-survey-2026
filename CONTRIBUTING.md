# Contributing to `rse-survey`

For developers extending analysis tasks, renderers, or Prefect pipelines.

## Dev setup

```bash
uv sync --extra dev
uv run pre-commit install
uv run pytest
```

## Layout

`src/rse_survey/` is organised as the pipeline runs. Each layer may import
the ones above it in this list, never the ones below — so if you are unsure
where code belongs, ask which stage it happens in.

| Package | Stage | Holds |
| --- | --- | --- |
| `config/` | 1 | `config/*.yml` → typed `BookConfig` / coding params; every repo path |
| `data/` | 2 | raw CSVs → the clean long-format answers table; input validation |
| `coding/` | 3 | free text → categories (offline HF: tokenize, cluster, label) |
| `analysis/` | 4 | clean table → summary tables, via registered tasks |
| `artifacts/` | 5 | generic writers: artifact dirs, markdown tables, bar charts |
| `book/` | 6 | artifacts → Quarto chapters under `rse-book/` |
| `flows/` | 7 | Prefect flows, one per CLI command |
| `cli.py` | — | argparse front end; each subcommand calls exactly one flow |

Two conventions worth knowing:

- **Flows stay thin.** `flows/` is the only place that imports Prefect. Real
  work lives in plain functions below it, so every step is testable without a
  Prefect runtime.
- **`artifacts/` is question-agnostic.** It knows how to write *a* table or
  *a* chart. Anything that knows what a *select question* is belongs with its
  task — see `analysis/tasks/select_questions/`.

## Add an analysis task

A task is anything with `name` and `run(self, ctx) -> TaskResult`.

1. Create `src/rse_survey/analysis/tasks/my_task.py` (or a subpackage, if it
   needs more than one module — see `select_questions/`, which splits into
   `grouping` / `summary` / `artifacts` / `run`)
2. Register it: `from rse_survey.analysis.registry import register`
3. Import the module from `ensure_builtin_tasks_loaded()` in `registry.py`
4. Add the task id to a question's `tasks:` list in `config/book.yml`
5. Add `tests/test_my_task.py` using `tests/fixtures/` (no real microdata)

Reuse before adding: `analysis/summarize/` already has categorical/likert
summarisation and answer-value recoding shared across tasks.

## Free-text coding

`coding/` reads top to bottom as the stages it performs: `tokenize` →
`seed_themes` → `embed` → `cluster` → `cluster_diagnostics` → `label` →
`token_labels`, with `workflows` wiring them into `propose` / `apply`.

`token_labels.csv` is the handoff to analysis and the file humans edit —
nothing downstream imports the clustering internals.

## Input contract

Changing required columns or files → update
[docs/input-format.md](docs/input-format.md), `data/validation.py`, and tests
together.

## Pre-commit

Ruff lint/format plus basic file hygiene. Keep hooks fast; run `pytest`
separately (or in CI).
