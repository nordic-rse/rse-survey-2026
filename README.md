# International RSE Survey analysis package

Analyse the International RSE Survey for **your focus country** (or country
group), build tables/figures as artifacts, and publish a thin Quarto book.

## What you need

1. Survey files under `RSE_survey_2026_data/` — see [docs/input-format.md](docs/input-format.md)
2. Python 3.11+ (via [uv](https://github.com/astral-sh/uv) or conda)

## Install

```bash
# uv (recommended)
uv sync --extra dev
# optional HF coding extras:
# uv sync --extra dev --extra hf

# or conda
mamba env create -f environment.yml
mamba activate rse-survey
```

## Configure your report

Edit [`config/book.yml`](config/book.yml):

- `focus` — who the report is about
- `presentation` — select-question chapter content: `table` | `graphic` | `both`
- `questions.<id>.category_order` — optional answer-label order (omit/`null` = by frequency)
- `questions.<id>.category_labels` — optional raw survey label → shorter display label (tables/plots)
- `questions.<id>.category_groups` — optional aggregate several raw labels into one display category
- `questions.<id>.response_kind: categorical_with_other` — closed options only in tables/plots; requires `closed_categories`; writes `other_by_country` lists
- `age_groups` — how `socio3_0` bands map to report groups
- `compare_groups` — countries for between-country views
- `questions` — which survey items appear, and which tasks to run

First-test defaults: **Germany** focus; compare Netherlands / UK / US;
single-year **2026** (`waves.include`).

## Run

Global flags: `--silent` | `--verbose` (default) | `--debug`
(before or after the subcommand). With `--debug`, Prefect flows return and
print their result payload; otherwise they return nothing to the CLI.

```bash
# Check data + config
uv run rse-survey validate

# Process raw CSV → clean long-format table (required before analysis)
uv run rse-survey process-data

# Build artifacts for all questions in book.yml
uv run rse-survey build-artifacts

# Or one question while iterating
uv run rse-survey build-artifacts --question edu1_0

# Select-question table + horizontal bar (focus | by_age | between_countries)
uv run rse-survey select-questions --question rse1_0 --grouping focus
uv run rse-survey select-questions --question rse1_0 --grouping by_age
uv run rse-survey select-questions --question rse1_0 --grouping between_countries
```

Outputs: clean data in `rse-book/_data/`; artifacts in
`rse-book/_artifacts/<question_id>/` (including `focus.png`,
`by_age.png`, `between_countries.png` for select questions).

### Free-text HF coding

Configs: [`config/free_text_coding.yml`](config/free_text_coding.yml) (needs `[hf]` extras).
Each entry is coding params (`k`, `model`, `labels`, …) plus optional `text_column`
(defaults to the question id). Answers come from the **focus slice** of the
clean long table (run `process-data` first).

Workflow:

1. **Cluster + draft labels once** (writes YAML `labels` + editable CSV):

```bash
uv run rse-survey propose --question skill2 --overwrite-labels
```

2. **Review cluster names** in `config/free_text_coding.yml`, then broadcast
   them to every token:

```bash
uv run rse-survey apply --question skill2
```

3. **Reallocate or drop individual tokens** in
   `rse-book/_hf_freetext_cache/<qid>/token_labels.csv`:
   - edit `category_human` (leave `category_llm` as the model draft)
   - set `exclude` to `1` to drop a token from analysis (default `0`)

   Then refresh the summary:

```bash
uv run rse-survey apply --question skill2 --from-csv
```

4. **Follow-up** (`build-artifacts`, appendix) reads `token_labels.csv`.

```bash
uv run rse-survey build-artifacts --question skill2
```

```bash
uv run rse-survey sync-quarto
cd rse-book && quarto render
```

Plot titles live in the PNGs under `rse-book/_artifacts/` (not in Quarto).
After changing plotting code, regenerate artifacts, then force the book copy:

```bash
uv run rse-survey select-questions --question rse1_0 --grouping focus
uv run rse-survey select-questions --question rse1_0 --grouping by_age
uv run rse-survey select-questions --question rse1_0 --grouping between_countries
uv run rse-survey sync-quarto   # overwrites rse-book/_book/_artifacts/
cd rse-book && quarto render chapters/rse1_0.qmd
```

Nuclear option if a page still shows an old image:

```bash
rm -rf rse-book/_book/_artifacts
cd rse-book && quarto render
```

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) to add analysis tasks or graphics.
