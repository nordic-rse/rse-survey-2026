# Required survey input format

This document is the contract that `rse-survey validate` and the
`validate_inputs` Prefect task enforce for **raw** inputs. Downstream
analysis reads the clean long-format table produced by
`rse-survey process-data`.

## Pipeline order

1. Place raw files under `data_dir`
2. `rse-survey validate`
3. `rse-survey process-data` → writes `rse-book/_data/clean_long.csv`
4. `rse-survey propose` / `apply` (optional) and `rse-survey build-artifacts`

## Files under `data_dir` (default: `RSE_survey_2026_data/`)

| File | Role |
|------|------|
| `2026_tf.csv` | One row per respondent; question answers + `socio1_0` country |
| `2026_all_cols.csv` | Question/option metadata (`New_name`, `Question`, `Option`, …) |

Microdata are **not** committed to git. Place them locally before running flows.

## Required columns in `2026_tf.csv`

| Column | Purpose |
|--------|---------|
| `submitdate_0` | Non-empty ⇒ submitted response (partials dropped) |
| `socio1_0` | Country name (e.g. `Germany`, `United Kingdom`, `United States`) |
| `socio3_0` | Age band labels (see `config/book.yml` `age_groups`) |
| `Year_0` | Survey year (filtered via `waves.include` in `book.yml`) |

Question columns are named after the question id (`edu1_0`) or multi-select
pattern `org2can[SQ001]_0`.

## Country name spellings

Use the spellings present in `socio1_0` (2026):

- `Germany`, `Netherlands`, `United Kingdom`, `United States`, …

## What `validate_inputs` checks

1. `config/book.yml` parses and has `focus.countries` + `questions`
2. `data_dir` exists with both CSVs
3. Required columns present
4. At least one submitted respondent in focus countries (**error** if zero)
5. Each question id matches ≥1 column (**warning** if missing)
6. Free-text questions with `appendix: true` should have an entry in
   `config/free_text_coding.yml` (**warning** if missing)

## Clean long-format output (`rse-book/_data/`)

`rse-survey process-data` writes:

| File | Role |
|------|------|
| `clean_long.csv` | One row per respondent × answered question cell |
| `meta.json` | Row/respondent counts, countries, years, question ids |

### Schema

| Column | Meaning |
|--------|---------|
| `row_id` | Respondent id |
| `country` | Country (`socio1_0`) |
| `country_group` | Mapped `compare_groups` label |
| `year` | Survey year |
| `age_group` | Mapped `age_groups` label (may be empty if unmapped) |
| `question_id` | Configured question stem |
| `option_code` | Multi-select bracket code; empty for single-response |
| `value` | Decoded answer (option label or text) |

Processing steps: load raw → select variables of interest → filter
countries (focus + compare) → filter years (`waves.include`) → add
`age_group` / `country_group` → melt + decode → save.

## Free-text coding

`rse-survey propose` / `apply` read answers from the **focus slice** of
`clean_long.csv` (run `process-data` first). `config/free_text_coding.yml`
holds coding params (`k`, `model`, `labels`, …), not file paths.

## Minimal test fixture

See `tests/fixtures/` for a tiny CSV pair used by unit tests (no real microdata).
