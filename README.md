# rse-survey-report

Python package for the analysis and reporting of the International RSE Survey
2026. The package makes a Quarto book with one chapter per survey question. It
also contains an overview notebook and slides for the survey meeting.

## Setup

The package needs Python 3.14 or later and [uv](https://docs.astral.sh/uv/).
The book and the slides also need [Quarto](https://quarto.org/).

```bash
uv sync
uv run pre-commit install
```

## Data

The data are not in this repository. Put the survey exports in
`data/<year>/` at the repository root:

- `data/2026/2026_tf.csv`: one row per respondent, with the responses and
  the country (`socio1_0`).
- `data/2026/2026_all_cols.csv`: the question text and the answer options.

The analyses use only the submitted responses. These are the rows with a
value in `submitdate_0`.

## Repository structure

| Path | Purpose |
|------|---------|
| [`src/rse_survey_report/config.py`](src/rse_survey_report/config.py) | Country groups, answer levels, age groups and question categories |
| [`src/rse_survey_report/utils.py`](src/rse_survey_report/utils.py) | Load and preprocess the survey data |
| [`src/rse_survey_report/codebook.py`](src/rse_survey_report/codebook.py) | Codebook with the question text and allowed answers per response column |
| [`src/rse_survey_report/plotting.py`](src/rse_survey_report/plotting.py) | One plot function per question type |
| [`src/rse_survey_report/book.py`](src/rse_survey_report/book.py) | Write the book chapters and `book/_quarto.yml` |
| [`book/`](book/) | Quarto book; [`index.qmd`](book/index.qmd) is the landing page |
| [`notebooks/overview.py`](notebooks/overview.py) | Overview notebook in jupytext percent format |
| [`slides/survey-meeting.qmd`](slides/survey-meeting.qmd) | Slides for the survey meeting |
| [`tests/unit/`](tests/unit/) | Unit tests |

## Configuration

[`config.py`](src/rse_survey_report/config.py) holds the settings:

- `NORDICS` is the set of countries for the chapter analyses.
- `COMPARE_GROUPS` are the country groups for the "Between countries" section.
- `AGE_GROUPS` maps the age answers (`socio3_0`) to three age groups.
- `CATEGORIES` sets the book parts and the questions in each part.

## Build the outputs

Run these commands from the repository root.

Build the book:

```bash
make book
```

This command deletes `book/_freeze/`. Then it writes the chapters and
`book/_quarto.yml` from the codebook. Then it renders the book to
`book/_book/`. Open `book/_book/index.html`.

Do not edit `book/chapters/` or `book/_quarto.yml`. The next build replaces
them.

Render the slides:

```bash
make slides
```

Make the `.ipynb` file for the overview notebook:

```bash
make notebook
```

## Publish the book

The book is on GitHub Pages at
<https://nordic-rse.github.io/rse-survey-2026/>.

CI has no survey data. CI renders the book from the committed chapters and
the results in `book/_freeze/`.

1. Build the book with the survey data:

   ```bash
   make book
   ```

2. Commit `book/chapters/`, `book/_quarto.yml` and `book/_freeze/` together
   with the code changes.

3. Push to `main`. The `Publish Quarto book` workflow deploys the book to
   the `gh-pages` branch when `book/` changes. You can also start it from
   the Actions tab.

## Development

| Command | Purpose |
|---------|---------|
| `make test` | Run the tests with `pytest` |
| `make checks` | Run all pre-commit hooks (ruff, mypy and others) on all files |
| `make checks-all` | Fix the lint errors and format the code with ruff |

The mypy hook uses the staged version of each file. Stage the files that
import from each other together.

## How to cite

Bockting, F. & Wittke, S. (2026). Analysis Book for the International RSE
Survey 2026 (Nordic Focus) (Version 0.1.0). Zenodo.
https://doi.org/10.5281/zenodo.21716004
