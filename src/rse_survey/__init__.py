"""rse_survey: modular International RSE Survey analysis.

The package is organised as the pipeline runs, each layer depending only on
those below it:

1. :mod:`rse_survey.config`    — ``config/*.yml`` → typed objects
2. :mod:`rse_survey.data`      — raw CSVs → clean long-format table
3. :mod:`rse_survey.coding`    — free text → categories (offline HF)
4. :mod:`rse_survey.analysis`  — clean table → summary tables
5. :mod:`rse_survey.artifacts` — summaries → CSV / markdown / PNG
6. :mod:`rse_survey.book`      — artifacts → Quarto site
7. :mod:`rse_survey.flows`     — Prefect orchestration, one flow per command

:mod:`rse_survey.cli` is the argparse front end over the flows.
"""

__version__ = "0.1.0"
