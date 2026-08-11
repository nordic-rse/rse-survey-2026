# Kickoff: the `rse-survey` repository

Notes for introducing this repository to new collaborators. Written to be read
top-to-bottom in a meeting; each section is a talking point with the concrete
commands and file paths behind it.

---

## 1. The one-minute pitch

`rse-survey` turns the International RSE Survey microdata into a **country-focused
report**. It is a small Python package plus a Quarto book, and it is
**config-driven**: what appears in the report is decided in
[config/book.yml](config/book.yml), not in code.

The mental model — four hops, each with a durable file on disk:

```
RSE_survey_2026_data/*.csv      raw microdata (local only, never committed)
        │  rse-survey process-data
        ▼
rse-book/_data/clean_long.csv   one row per respondent × question × option
        │  rse-survey build-artifacts        (+ propose/apply for free text)
        ▼
rse-book/_artifacts/<qid>/      focus.md/.png, by_age.*, between_countries.*, .csv
        │  rse-survey sync-quarto
        ▼
rse-book/chapters/<qid>.qmd     thin chapters that only `{{< include >}}` artifacts
        │  quarto render  →  GitHub Pages
```

Two properties worth stating explicitly, because they shape everything else:

- **Quarto runs no analysis.** Chapters are generated stubs that include
  committed artifacts. A book render can never disagree with the numbers you
  reviewed, and it does not need the microdata.
- **Every stage is re-runnable per question.** You can iterate on one question
  (`--question skill2`) without rebuilding the other 52.

Current scope: **53 questions** in `book.yml` — 26 categorical, 13
categorical-with-other, 8 Likert arrays, 6 free-text (all 6 in the recoding
appendix).

---

## 2. Repository tour: what happens in which folder

| Path | What it is | Who edits it |
| --- | --- | --- |
| [config/](config/) | The report definition: [book.yml](config/book.yml) (focus country, questions, tasks, label handling), [defaults.yml](config/defaults.yml) (shared column names / defaults), [free_text_coding.yml](config/free_text_coding.yml) (per-question clustering params + reviewed cluster names) | **Everyone** — this is the main collaboration surface |
| [src/rse_survey/](src/rse_survey/) | The package (see layer map below) | Developers |
| [tests/](tests/) | pytest suite + tiny synthetic CSVs in [tests/fixtures/](tests/fixtures/) — **no real microdata** | Developers |
| [docs/input-format.md](docs/input-format.md) | The input contract that `validate` enforces, and the `clean_long.csv` schema | Whoever changes required columns |
| `RSE_survey_2026_data/` | Raw survey CSVs, placed locally. **git-ignored** | Data holders |
| [rse-book/](rse-book/) | The Quarto book. `_data/` (clean table, ignored), `_artifacts/` (generated tables/figures), `_hf_freetext_cache/` (free-text coding freezes), `chapters/` + `index.qmd` + appendices (**generated**), [_quarto.yml](rse-book/_quarto.yml) (**hand-maintained** part/chapter ordering) | Mixed — see §7/§8 |
| [.github/workflows/publish-book.yml](.github/workflows/publish-book.yml) | Renders and publishes to `gh-pages` on push to `main` touching `rse-book/**` | CI |

### Layer map of the package

`src/rse_survey/` is laid out in pipeline order. **A layer may import the ones
above it, never below.** If you don't know where code belongs, ask which stage
it happens in ([CONTRIBUTING.md](CONTRIBUTING.md) has the same table).

| Package | Stage | Holds |
| --- | --- | --- |
| [config/](src/rse_survey/config/) | 1 | YAML → typed `BookConfig` / coding params; **every repo path lives in [paths.py](src/rse_survey/config/paths.py)** |
| [data/](src/rse_survey/data/) | 2 | raw CSV → clean long table; input validation ([readers](src/rse_survey/data/readers.py), [filters](src/rse_survey/data/filters.py), [columns](src/rse_survey/data/columns.py), [reshape](src/rse_survey/data/reshape.py), [validation](src/rse_survey/data/validation.py)) |
| [coding/](src/rse_survey/coding/) | 3 | free text → categories, offline HF: `tokenize → seed_themes → embed → cluster → cluster_diagnostics → label → token_labels`, wired by [workflows.py](src/rse_survey/coding/workflows.py) |
| [analysis/](src/rse_survey/analysis/) | 4 | clean table → summary tables via **registered tasks** ([registry.py](src/rse_survey/analysis/registry.py)) |
| [artifacts/](src/rse_survey/artifacts/) | 5 | question-agnostic writers: artifact dirs, markdown tables, [plots/](src/rse_survey/artifacts/plots/) |
| [book/](src/rse_survey/book/) | 6 | artifacts → Quarto chapters and `_quarto.yml` pruning |
| [flows/](src/rse_survey/flows/) | 7 | Prefect flows — **the only place that imports Prefect** |
| [cli.py](src/rse_survey/cli.py) | — | argparse front end; each subcommand calls exactly one flow |

The Prefect rule is the one to emphasise: real work is plain functions, so
everything is unit-testable without a Prefect runtime, and flows stay thin.

### CLI ↔ flow ↔ output

| Command | Flow | Writes |
| --- | --- | --- |
| `validate` | (direct call to `validate_inputs`) | nothing; exits non-zero on error, prints warnings |
| `process-data` | [flows/process_data.py](src/rse_survey/flows/process_data.py) | `rse-book/_data/clean_long.csv` + `meta.json` |
| `build-artifacts [--question ID]` | [flows/build_artifacts.py](src/rse_survey/flows/build_artifacts.py) | all configured tasks for each question → `_artifacts/<qid>/` |
| `select-questions --question ID --grouping G` | [flows/select_questions.py](src/rse_survey/flows/select_questions.py) | one view (`focus` \| `by_age` \| `between_countries`) |
| `propose` / `apply` / `sample-tokens` | [flows/code_free_text.py](src/rse_survey/flows/code_free_text.py) | `_hf_freetext_cache/<qid>/` |
| `sync-quarto` | [flows/sync_book.py](src/rse_survey/flows/sync_book.py) | `chapters/*.qmd`, `index.qmd`, appendices, and re-copies artifacts into `_book/_artifacts` |
| `list-tasks` | — | prints registered analysis tasks |

Global flags `--silent` / `--verbose` (default) / `--debug`; with `--debug`
flows also print their result payload.

---

## 3. The analysis-task idea (worth 3 minutes)

A "task" is anything with `name` and `run(ctx) -> TaskResult`, registered with
`@register`. A question's `tasks:` list in `book.yml` decides which run for it.

Registered today: `focus`, `by_age`, `between_countries` (three groupings over
one code path in
[analysis/tasks/select_questions/](src/rse_survey/analysis/tasks/select_questions/)),
`validate_inputs`, and `across_waves` (**a stub — see §9**).

Tasks receive an `AnalysisContext`: the config, the question, `focus_df`,
`compare_df`, and output directories. They return files; they never decide
where the book lives. That is why adding a new view is additive, not surgery.

---

## 4. Setup for a new collaborator

```bash
uv sync --extra dev              # or: uv sync --extra dev --extra hf
uv run pre-commit install
uv run pytest                    # 12 test modules / 62 tests, no microdata needed
uv run rse-survey list-tasks     # smoke test
```

Then drop `2026_tf.csv` and `2026_all_cols.csv` into `RSE_survey_2026_data/`
and run `uv run rse-survey validate`.

Conda alternative: `mamba env create -f environment.yml`. Quarto CLI is
separate (1.9.x in use here).

---

## 5. Minimal worked examples

Six small examples to present. **A–B and D–F need no microdata** — they run on
the six synthetic rows in [tests/fixtures/](tests/fixtures/), so every
collaborator can follow along on their own laptop. All outputs below are real
output from those fixtures.

### The demo config (paste once, reuse for A, B, F)

```bash
mkdir -p /tmp/rse-demo && cat > /tmp/rse-demo/book.yml <<'YAML'
data_dir: tests/fixtures        # synthetic 2026_tf.csv + 2026_all_cols.csv
processed_dir: /tmp/rse-demo    # keeps the demo out of rse-book/_data

focus:
  label: Germany
  countries: [Germany]

age_column: socio3_0
age_groups:
  "Under 35": ["25 to 34 years"]
  "35-44": ["35 to 44 years"]

compare_groups:
  Germany: [Germany]
  Netherlands: [Netherlands]

waves:
  year_column: Year_0
  include: [2026]

questions:
  edu1_0:
    title: "What is the highest level of education you have attained?"
    response_kind: categorical
    tasks: [focus, by_age, between_countries]
  org2can:
    title: "What would you hope to get out of such an organisation?"
    response_kind: categorical
    tasks: [focus, between_countries]
YAML
```

That is the whole contract: **under 30 lines of YAML is a report.** Nothing else
names a country, an age band, a question, or a task.

### Example A — raw rows → clean long table (the first two hops)

```bash
uv run rse-survey validate     --config /tmp/rse-demo/book.yml
uv run rse-survey process-data --config /tmp/rse-demo/book.yml \
                               --coding-config /tmp/rse-demo/no-coding.yml
# INFO rse_survey.process_data: wrote /tmp/rse-demo/clean_long.csv (3 respondents)
```

(`no-coding.yml` does not exist on purpose — a missing coding config simply
means "no free-text questions", which keeps the demo to two questions.)

Input — 6 rows of `tests/fixtures/2026_tf.csv` (abridged):

| submitdate_0 | socio1_0 | socio3_0 | Year_0 | edu1_0 | org2can[SQ001]_0 | org2can[SQ002]_0 |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-01-15 | Germany | 25 to 34 years | 2026 | PhD | True | False |
| 2026-01-16 | Germany | 35 to 44 years | 2026 | Master | True | True |
| 2026-01-17 | Netherlands | 25 to 34 years | 2026 | PhD | False | True |
| 2026-01-18 | United Kingdom | 45 to 54 years | 2026 | Bachelor | True | False |
| 2026-01-19 | United States | 18 to 24 years | 2026 | Master | False | False |
| 2025-01-20 | Germany | 25 to 34 years | **2025** | PhD | True | False |

Output — `/tmp/rse-demo/clean_long.csv`:

```csv
row_id,country,country_group,year,age_group,question_id,option_code,item,value
1,Germany,Germany,2026,Under 35,edu1_0,,,PhD
2,Germany,Germany,2026,35-44,edu1_0,,,Master
3,Netherlands,Netherlands,2026,Under 35,edu1_0,,,PhD
1,Germany,Germany,2026,Under 35,org2can,SQ001,,Networking
2,Germany,Germany,2026,35-44,org2can,SQ001,,Networking
2,Germany,Germany,2026,35-44,org2can,SQ002,,Training
3,Netherlands,Netherlands,2026,Under 35,org2can,SQ002,,Training
```

Four teaching points in one screen:

1. **6 raw rows → 3 respondents.** UK and US are dropped because the config
   never mentions them; the 2025 row is dropped by `waves.include`. Scope is a
   config decision, applied once, early.
2. **Wide → long.** `org2can[SQ001]_0` becomes `question_id=org2can` +
   `option_code=SQ001`, and only *selected* boxes produce rows — respondent 1
   has one `org2can` row, respondent 2 has two.
3. **Codes become labels here.** `SQ001` → `Networking` comes from
   `2026_all_cols.csv`; nothing downstream needs the codebook again.
4. **Grouping columns are precomputed.** `age_group` and `country_group` are
   materialised now, so every later task groups by a plain column.

`meta.json` next to it records counts, countries, years and question ids —
useful as the "did the data change?" receipt.

### Example B — clean rows → chapter artifacts (the third hop)

```bash
uv run rse-survey build-artifacts --config /tmp/rse-demo/book.yml
# INFO: loaded 5 focus row(s), 7 compare row(s)
# INFO: built 5 task runs
```

`rse-book/_artifacts/edu1_0/focus.md`:

```markdown
### What is the highest level of education you have attained? (Germany, N=2)

| category | n | pct |
| --- | --- | --- |
| PhD | 1 | 50.0 |
| Master | 1 | 50.0 |

![...](../_artifacts/edu1_0/focus.png?v=ecd6e0dd0b)
```

`by_age.md` from the same run carries the grouping column and per-group
denominators:

```markdown
| age_group | category | n | pct | N |
| --- | --- | --- | --- | --- |
| Under 35 | PhD | 1 | 100.0 | 1 |
| 35-44 | Master | 1 | 100.0 | 1 |
```

Points to make:

- **Three files per view**: `.csv` (the numbers), `.md` (the Quarto include),
  `.png` (the figure). Reviewers read the CSV; the book reads the MD.
- **`?v=` is a content hash** appended to the image path so browsers cannot
  serve a stale figure.
- **`N` is stated everywhere**, per group — 2 respondents here, and the table
  says so.
- **5 task runs** = 3 for `edu1_0` + 2 for `org2can`, exactly the `tasks:` lists.
- `org2can` additionally gets `other_by_country.{json,md}` and one
  `between_countries_<country>.png` per compared country — the shapes a
  `categorical_with_other` question produces.

⚠️ **Presenter warning:** artifact locations are fixed in
[config/paths.py](src/rse_survey/config/paths.py), *not* configurable — so this
demo writes into the real `rse-book/_artifacts/edu1_0/` and `org2can/`.
Afterwards, restore them with the real config:

```bash
uv run rse-survey build-artifacts --question edu1_0 --question org2can
```

(Or stop after Example A, which only writes to `/tmp`.)

### Example C — a config-only change (the 30-second demo, real data)

The point of this one: **no Python is touched, and only one question rebuilds.**

```yaml
# config/book.yml
edu1_0:
  category_labels:
    "General University Entrance Qualification (or similar)": "General university entrance qualification"
  category_order: ["Promotion/PhD", "Masters Degree", ...]   # or omit → by frequency
```

```bash
uv run rse-survey build-artifacts --question edu1_0   # ~seconds
uv run rse-survey sync-quarto
cd rse-book && quarto render chapters/edu1_0.qmd
```

Say out loud: `process-data` was **not** needed, because the set of columns did
not change — only their presentation. That is the boundary between §7 and §8.

### Example D — a whole new analysis task in ~25 lines

Shows the extension point: registry + context in, `TaskResult` out.

```python
# src/rse_survey/analysis/tasks/demo_count.py
"""Demo task: how many focus respondents answered this question."""

from __future__ import annotations

from rse_survey.analysis.context import AnalysisContext, TaskResult
from rse_survey.analysis.registry import register
from rse_survey.artifacts.layout import question_artifact_dir
from rse_survey.artifacts.tables import write_table_artifact


@register
class DemoCountTask:
    name = "demo_count"

    def run(self, ctx: AnalysisContext) -> TaskResult:
        qid = ctx.question.question_id
        rows = ctx.focus_df.loc[ctx.focus_df["question_id"] == qid]
        if rows.empty:
            return TaskResult(
                task_name=self.name, question_id=qid, skipped=True,
                skip_reason=f"no focus answers for {qid}",
            )
        table = (
            rows.groupby("age_group", observed=True)["row_id"]
            .nunique().reset_index(name="respondents")
        )
        files = write_table_artifact(
            question_artifact_dir(ctx.artifacts_dir, qid),
            "demo_count", table, heading=f"Respondents per age group ({qid})",
        )
        return TaskResult(task_name=self.name, question_id=qid, files=files)
```

Two more lines make it real — add `demo_count` to the import in
`ensure_builtin_tasks_loaded()`
([analysis/registry.py](src/rse_survey/analysis/registry.py)), and add
`demo_count` to a question's `tasks:` list:

```console
$ uv run rse-survey list-tasks
across_waves
between_countries
by_age
demo_count          ← new
focus
validate_inputs

$ cat rse-book/_artifacts/edu1_0/demo_count.md
### Respondents per age group (edu1_0)

| age_group | respondents |
| --- | --- |
| Under 35 | 1 |
| 35-44 | 1 |
```

What this demonstrates about the architecture:

- The task never learns where the book lives, which country is in focus, or how
  a table becomes markdown — `ctx` and `artifacts/` handle that.
- No Prefect import, so `tests/test_my_task.py` calls `run()` directly.
- Skipping is a normal return value, not an exception: one bad question cannot
  fail the book build.

### Example E — free-text: what human review actually changes

`rse-book/_hf_freetext_cache/skill2/token_labels.csv` after `propose` + `apply`
(real rows, abridged):

```csv
token,category_llm,category_human,cluster_id,n,exclude
agent based modelling on hpc infrastructure,AI And Automation,AI And Automation,5,1,0
agentic coding,AI And Automation,AI And Automation,5,2,0
ai agent assisted development,AI And Automation,AI And Automation,5,1,0
```

A reviewer edits **only** `category_human` and `exclude` — `category_llm` stays
as the model's draft, so the audit trail survives:

```csv
token,category_llm,category_human,cluster_id,n,exclude
agentic coding,AI And Automation,Coding And Development,5,2,0
ai,AI And Automation,AI And Automation,5,4,1
```

```bash
uv run rse-survey apply --question skill2 --from-csv    # keeps your edits
uv run rse-survey sample-tokens --question skill2 -n 10 # eyeball the result
uv run rse-survey build-artifacts --question skill2     # → focus/by_age/… + token_allocation
```

Result — `category_summary.csv` is recomputed from the human column, and the
book's recoding appendix shows every token's home:

```csv
category,n
Coding And Development,60
Soft Skills And Collaboration,49
Project Management,42
```

The story to tell: **the model proposes, a human decides, and the decision is a
reviewable CSV in the repository** — not a prompt, not a notebook cell. Full
loop and the destructive-step warning in §10.

### Example F — what "temporal analysis" hits today (2-minute honest demo)

Flip one line in the demo config and re-run Example A:

```yaml
waves:
  include: [2025, 2026]
```

```console
INFO rse_survey.process_data: wrote /tmp/rse-demo/clean_long.csv (4 respondents)

row_id,country,year,question_id,value
1,Germany,2026,edu1_0,PhD
2,Germany,2026,edu1_0,Master
3,Netherlands,2026,edu1_0,PhD
4,Germany,2025,edu1_0,PhD      ← the 2025 respondent is now in scope
```

So the data layer is already wave-aware. Now ask for the analysis by adding
`across_waves` to the question's `tasks:`:

```console
INFO rse_survey.analysis.build: skip edu1_0/across_waves: across_waves not implemented yet
```

That single log line is the entire status of multi-wave support, and it frames
§9 precisely: the missing pieces are **a second data source, a crosswalk, and
the task body** — not a redesign.

---

## 6. Standard working loop

```bash
uv run rse-survey validate
uv run rse-survey process-data                        # after data or question-set changes
uv run rse-survey build-artifacts --question rse1_0    # iterate on one question
uv run rse-survey sync-quarto
cd rse-book && quarto render
```

**Cache gotcha to mention out loud:** plot titles live *inside* the PNGs, and
Quarto happily keeps a stale copy in `_book/`. `sync-quarto` re-copies
artifacts over `_book/_artifacts/` for exactly this reason. If a page still
shows an old figure: `rm -rf rse-book/_book/_artifacts && quarto render`.

---

## 7. Updating an existing question in the book

Nearly always a `config/book.yml` edit — no Python.

1. **Find the question block** under `questions:` (keyed by survey id, e.g.
   `edu1_0`).
2. **Change what you need:**
   - `title:` — chapter title and heading.
   - `tasks:` — which views appear (`focus`, `by_age`, `between_countries`).
   - `category_order:` — explicit answer order; omit or `null` = by frequency.
     Note the order is bottom-up in horizontal bars, so lists usually read
     "highest category first".
   - `category_labels:` — raw survey label → shorter display label. Keys must
     match the data **exactly**, including punctuation.
   - `category_groups:` — aggregate several raw values into one display
     category. A value may appear in only one group (the loader raises
     otherwise). If you group *and* order, `category_order` must use the **new**
     group names.
   - `response_kind:` — `categorical` | `categorical_with_other` (requires
     `closed_categories`) | `likert` | `free_text`.
   - `presentation:` (top level) — `table` | `graphic` | `both`.
3. **Rebuild just that question** and sync:

   ```bash
   uv run rse-survey build-artifacts --question edu1_0
   uv run rse-survey sync-quarto
   cd rse-book && quarto render chapters/edu1_0.qmd
   ```

   `process-data` is only needed again if you changed *which* columns are
   selected (new question id, new alias, changed year/country filters).

**Do not hand-edit these — `sync-quarto` overwrites them:**
`rse-book/chapters/*.qmd`, `index.qmd`, `about/user-guide.qmd`,
`appendices/recoding.qmd`, `appendices/methodology.qmd`. Front matter changes
belong in [book/chapters.py](src/rse_survey/book/chapters.py). `_quarto.yml`
is the exception: it is hand-maintained (sync only *prunes* entries for
questions no longer in `book.yml`).

---

## 8. Adding a new question

1. **Check the raw column exists.** Question columns are named after the id
   (`edu1_0`) or use the multi-select pattern `org2can[SQ001]_0`.
   `validate` warns (does not fail) when an id matches no column.
2. **Add the block to `config/book.yml`:**

   ```yaml
   genAI7_0:
     title: "..."
     response_kind: categorical        # or categorical_with_other / likert / free_text
     tasks: [focus, by_age, between_countries]
     # closed_categories: [...]        # required for categorical_with_other
     # appendix: true                  # free text you want in the recoding appendix
   ```
3. **Odd column shapes?** If one logical question spans several raw stems
   (paired Actual/Desired arrays, per-country variants like `tool5`/`tool5can`),
   add it to `QUESTION_ALIASES` in
   [data/columns.py:12](src/rse_survey/data/columns.py#L12) and, for paired
   arrays, set `item_conditions:` (+ optional `item_order:`) as `likert01` does.
4. **Re-run the pipeline** — `process-data` is required here, because column
   selection changed:

   ```bash
   uv run rse-survey validate
   uv run rse-survey process-data
   uv run rse-survey build-artifacts --question genAI7_0
   ```
5. **Place the chapter** in [rse-book/_quarto.yml](rse-book/_quarto.yml) under
   the right `- part:`. Without this the chapter file exists but is not in the
   book.
6. **Free text?** Also add an entry to `config/free_text_coding.yml` and follow
   §10 (`validate` warns if `appendix: true` free text has no coding entry).
7. `uv run rse-survey sync-quarto && cd rse-book && quarto render`.

Rule of thumb: **config-only change → `build-artifacts`; question-set change →
`process-data` first.**

---

## 9. Adding a previous wave for temporal analysis

Be honest about this one in the meeting: **the plumbing exists, the analysis
does not.** Present it as the first substantial piece of new work.

What already exists:

- `waves.year_column` / `waves.include` in `book.yml`, and a year filter
  ([data/filters.py:77](src/rse_survey/data/filters.py#L77)).
- `year` is a first-class column in `clean_long.csv`.
- Chapters already know how to include an `across_waves.md` artifact
  ([book/chapters.py:11](src/rse_survey/book/chapters.py#L11)).

What is missing or hard-wired:

- **Readers are single-wave.** [data/readers.py](src/rse_survey/data/readers.py)
  hard-codes `2026_tf.csv` and `2026_all_cols.csv` inside one `data_dir`.
- **`across_waves` is a stub** that always returns `skipped`
  ([analysis/tasks/across_waves.py](src/rse_survey/analysis/tasks/across_waves.py)),
  and no question lists it in `tasks:`.
- **Harmonisation is unsolved and is the real project**: question ids and
  `New_name` values drift between waves, answer-option wording changes, country
  spellings change, and age bands may differ. None of that is expressible in
  today's config.

Suggested plan (a good first design discussion):

1. **Config shape.** Extend `waves:` to a list of wave sources, e.g.
   `waves: sources: [{year: 2026, dir: RSE_survey_2026_data, tf: 2026_tf.csv, cols: 2026_all_cols.csv}, {year: 2022, ...}]`.
   Decide whether `data_dir` stays as the single-wave shorthand.
2. **Readers + loader.** Make `load_raw` return per-wave frames and let
   `process_data_flow` concatenate after per-wave selection/decoding. Tag every
   row with `year` from its source, not only from a column.
3. **Crosswalk.** Add a per-question, per-wave mapping (column stem, answer
   value recodes) — probably `waves.crosswalk` in config, applied in a new
   `data/` module. This is where "same question, different wording" gets
   decided, and it is a **content** decision, not a code one: budget
   collaborator time for it.
4. **Comparability policy.** Write down what counts as comparable (identical
   options? collapsed groups? changed sampling frame?) and make
   non-comparable pairs fail loudly rather than plot silently.
5. **Implement the task.** Replace the stub: group by `year` (reuse
   `summarize_by_group` from
   [analysis/summarize/categorical.py](src/rse_survey/analysis/summarize/categorical.py)),
   write `across_waves.csv/.md/.png` via the existing writers, honour
   `presentation`. Denominators per wave, and always show wave *n*.
6. **Validation + docs + tests.** Extend
   [data/validation.py](src/rse_survey/data/validation.py) (each wave file
   present, required columns per wave, year values as configured), update
   [docs/input-format.md](docs/input-format.md), and add a two-wave fixture
   pair under `tests/fixtures/`. These three move together by convention.
7. **Enable per question** by adding `across_waves` to `tasks:` only where the
   crosswalk says the item is comparable.

Also note: `index.qmd` currently states that wave views are disabled, and it is
generated by `germany_index()` in
[book/chapters.py:73](src/rse_survey/book/chapters.py#L73) — that text needs to
change with the feature.

---

## 10. Updating free-text answers (HF coding)

The offline pipeline that turns free text into categories. Needs the `hf`
extras: `uv sync --extra dev --extra hf`.

**Design point to convey:** clustering is a *draft*; humans own the categories.
`token_labels.csv` is the single source of truth and the handoff to analysis —
nothing downstream imports the clustering internals.

Per question, the freeze lives in `rse-book/_hf_freetext_cache/<qid>/`:
`cluster_assignments.csv`, `token_labels.csv`, `category_summary.csv`,
`token_categories.csv`, `meta.json` (`embeddings.npy` and
`labels_proposed.json` are git-ignored as regenerable).

### The loop

```bash
# 0. text comes from the FOCUS slice of clean_long.csv
uv run rse-survey process-data

# 1. cluster + draft labels (writes YAML `labels:` and the editable CSV)
uv run rse-survey propose --question skill2 --overwrite-labels

# 2. review cluster names in config/free_text_coding.yml, then broadcast
uv run rse-survey apply --question skill2

# 3. fix individual tokens in _hf_freetext_cache/skill2/token_labels.csv
#    - edit `category_human`   (leave `category_llm` as the model draft)
#    - set `exclude` to 1 to drop a token
uv run rse-survey apply --question skill2 --from-csv

# 4. inspect, then rebuild the question and the appendix
uv run rse-survey sample-tokens --question skill2 -n 15
uv run rse-survey build-artifacts --question skill2
uv run rse-survey sync-quarto
```

`token_labels.csv` columns: `token`, `category_llm`, `category_human`,
`cluster_id`, `n`, `exclude`.

### Which step for which change

| You want to… | Do |
| --- | --- |
| Rename a category | Edit `labels:` in `free_text_coding.yml` → `apply` |
| Move / drop individual tokens | Edit `token_labels.csv` → `apply --from-csv` |
| Change `k`, embedding model, seed themes | Edit params → `propose --overwrite-labels` (**discards manual token edits**) |
| Add a new free-text question | New `free_text_coding.yml` entry + `response_kind: free_text`, `appendix: true` in `book.yml` → run the whole loop |
| New microdata arrived | `process-data`, then re-`propose` (tokens changed) |

Two warnings for the meeting:

- **`propose` is destructive to human work.** `apply --from-csv` is the
  low-risk path; reach for `propose` only when the clustering itself is wrong.
- Free-text questions only get `focus` / `by_age` / `between_countries` views
  **after** `token_labels.csv` exists; before that the task skips with a
  message naming the missing file.

Params per question (`free_text_coding.yml`): `k` or
`cluster_method: hdbscan`, `model` (embeddings, e.g.
`intfloat/multilingual-e5-base`), `label_model` (e.g. `Qwen/Qwen2.5-7B-Instruct`,
`label_load: 4bit`), `embed_context`, `n_examples`, `random_state: 42`.
12 questions have entries today; 6 are in the appendix.

---

## 11. Technical dependencies worth discussing

| Area | What | Why it matters in a meeting |
| --- | --- | --- |
| Python | ≥3.11 (env pins 3.12) | Modern typing syntax used throughout |
| Env manager | **uv** (`uv.lock` committed) or conda `environment.yml` | Agree on one so lockfile churn stays meaningful |
| Core | pandas ≥2, numpy, pyyaml | — |
| Plotting | **plotnine** ≥0.13 + matplotlib | ggplot-style; figures are PNGs with baked-in titles (§6 cache gotcha) |
| Orchestration | **Prefect** (`>=2.14`, resolved **3.8.2**) | The big "do we need this?" question. Today it buys per-question task runs and logging; the wide `>=2.14` range spanning a major version is worth tightening |
| Book | **Quarto CLI** (1.9.x here), published via `quarto-actions` to `gh-pages` | Not a Python dep — every collaborator must install it separately. CI only fires on pushes to `main` touching `rse-book/**` |
| HF extras (`[hf]`) | sentence-transformers, scikit-learn, umap-learn, hdbscan, transformers, accelerate, **torch**, **bitsandbytes**, numba/llvmlite pins | Heavyweight and the main portability risk: `label_load: 4bit` effectively wants a CUDA GPU, and umap/numba pins are fragile. Decide who runs coding, and treat committed freezes as the shared artifact so most people never install this |
| Dev | pytest (`hf` marker for model-dependent tests), pre-commit (ruff lint+format, trailing whitespace, YAML check, 2 MB file cap) | `pytest` is deliberately **not** a pre-commit hook — run it separately or in CI |
| Data governance | Microdata git-ignored; fixtures are synthetic; artifacts + HF freezes are committed | Ground rule for new collaborators: **never commit `RSE_survey_2026_data/` or `_data/`.** Also: `_artifacts/` and `other_by_country.*` contain verbatim free-text "other" answers — re-identification risk is a real review item |
| Reproducibility | Artifacts committed rather than rendered on demand; `random_state: 42`; freezes checked in | Reviewable numbers, but the repo must be re-buildable from raw data on request |

There is no CI job for `pytest` or `ruff` yet — only the book publish workflow.
Adding one is a cheap, high-value first contribution.

---

## 12. State of the repo before you present it

Check these before the meeting; two are blockers for anyone trying to clone.

1. **The Python package is not in git.** `src/`, `config/`, `tests/`, `docs/`,
   `pyproject.toml`, `uv.lock`, `CONTRIBUTING.md`, `.pre-commit-config.yaml`,
   `environment.yml`, `rse-book/_artifacts/`, `rse-book/_hf_freetext_cache/`
   are all still **untracked** on `feat/hf-freetext-coding`. `HEAD` contains
   only the legacy R-era tree. A new collaborator cloning today gets none of
   what this document describes.
2. **The legacy R pipeline is deleted in the working tree but not committed**
   (`rse-book/R/`, `rse-book/_freeze/`, `insights.qmd`, `insights.html`,
   `RSE_survey_insights_helper/`, `RSE_survey_outline/`, `rse-book/_book.zip`).
   Decide whether that removal is part of the same commit and whether anything
   from the R era must be preserved for provenance.
3. **`book.yml` is still the "first test" config**: focus **Germany**, comparing
   NL/UK/US, single year 2026 — in a `nordic-rse` repository. The Germany focus
   is also hard-coded in `germany_index()` for the book landing page. Agree on
   the real focus, and on making the landing page focus-driven.
4. **`across_waves` is a stub** (§9) and `index.qmd` says so.
5. `uv run pytest` and `uv run pre-commit run --all-files` should be green
   before you present — run them the morning of.

---

## 13. Suggested 45-minute agenda

| Min | Topic |
| --- | --- |
| 0–5 | §1 pitch + the four-hop diagram on screen |
| 5–11 | §2 repo tour, then open `config/book.yml` and read one question block aloud |
| 11–20 | §5 examples **A + B** live on the fixtures: 6 rows → `clean_long.csv` → `focus.md` |
| 20–24 | §5 example **C**: config-only change on real data, rebuild one question, render one chapter |
| 24–29 | §5 example **D**: the 25-line task — the extension point |
| 29–34 | §5 example **E** + §10: free-text human-in-the-loop with a real `token_labels.csv` |
| 34–39 | §5 example **F** + §9: multi-wave — what exists, what is missing, and the harmonisation question for the group |
| 39–43 | §11 dependencies + data-handling ground rules |
| 43–45 | §12 repo state, ownership, first tasks |

### Good first tasks to hand out

- Add one new question end to end (§8) — teaches the whole pipeline in an hour.
- Review one free-text question's `token_labels.csv` (§10) — no HF install
  needed, `apply --from-csv` only.
- Add a `pytest` + `ruff` GitHub Actions workflow (§11).
- Draft the wave crosswalk config shape (§9, step 1) as a design note.
