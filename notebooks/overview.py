# ---
# jupyter:
#   jupytext:
#     cell_metadata_filter: -all
#     formats: ipynb,py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.19.5
#   kernelspec:
#     display_name: .venv
#     language: python
#     name: python3
# ---

# %% [markdown]
# # International RSE Survey 2026: overview
#
# The International RSE Survey asks people who write software for research
# about their role, employment, work, training, funding, tools and use of
# generative AI.
#
# This notebook gives a first look at the 2026 data:
#
# 1. **Data**: the files and the respondents.
# 2. **Survey structure**: the topics and the country-specific questions.
# 3. **Question types**: the answer formats and one example plot for each.
# 4. **Group comparisons**: the same plots, split by age group.
#
# The detailed results for each question are in the Quarto book (`book/`).

# %%
import pandas as pd
import plotly.express as px
from IPython.display import display

from rse_survey_report.codebook import build_codebook
from rse_survey_report.config import CATEGORIES, NORDICS
from rse_survey_report.plotting import (
    plot_agreement,
    plot_bool,
    plot_choice,
    plot_likert,
    plot_likert2,
)
from rse_survey_report.utils import (
    add_age_group,
    get_counts_question_country,
    get_data_path,
    load_data,
    prepare_questions,
    preprocess_data,
)

# %% [markdown]
# ## 1. Data
#
# The analysis uses two files in `data/2026/`:
#
# - `2026_tf.csv`: one row for each respondent. The column order is the
#   order of the questions in the survey.
# - `2026_all_cols.csv`: the question text and the answer options for each
#   column.
#
# A response without a submit date (`submitdate_0`) is partial. The column
# `complete` shows if the respondent submitted the survey.

# %%
path = get_data_path(file="2026_tf.csv", year=2026)
df_raw = load_data(path)
df_clean = preprocess_data(df_raw, excl_var="submitdate_0")
df_clean.head()

# %% [markdown]
# ### Respondents by country
#
# The first question asks for the country of work (`socio1_0`). The table
# shows the 20 countries with the most responses.

# %%
(
    df_clean.groupby("country")
    .agg(total=("complete", "size"), complete=("complete", "sum"))
    .assign(partial=lambda d: d["total"] - d["complete"])
    .sort_values(["total", "country"], ascending=[False, True])
    .head(n=20)
)

# %% [markdown]
# ## 2. Survey structure
#
# ### Topics
#
# The survey starts with the country and ends with demographics. Between
# these, the questions follow the topics below, in survey order.

# %%
pd.DataFrame(
    {
        "category": list(CATEGORIES),
        "n_questions": [len(ids) for ids in CATEGORIES.values()],
        "ids": [", ".join(ids) for ids in CATEGORIES.values()],
    }
)

# %% [markdown]
# ### Country-specific questions
#
# The survey routes some respondents to extra questions:
#
# - **Country routing.** The country answer (`socio1_0`) opens extra
#   questions for some countries. A suffix in the question id shows the
#   country, e.g. `nord` (Nordics), `de` (Germany), `uk`, `us`, `can`
#   (Canada), `zaf` (South Africa).
# - **Answer routing.** Some answers open a follow-up question, e.g. a
#   "Yes" to `conf1can` opens `conf2can`.
#
# `RSE_survey_outline/survey-process.md` lists all routing rules. The table
# below counts the respondents for each question and country.

# %%
counts = get_counts_question_country(df_clean)
df_cols = load_data(get_data_path("2026_all_cols.csv", 2026))
df_questions = prepare_questions(df_cols, counts)

print(df_questions)

# %% [markdown]
# ### Questions for the Nordic countries
#
# The rest of this notebook uses the Nordic respondents
# (Finland, Norway, Sweden, Denmark, Iceland, Estonia). The table lists the
# questions with at least one Nordic response.

# %%
df_nordics = df_clean[df_clean["country"].isin(NORDICS)]
df_nordics_quest = df_questions[
    df_questions["country"].isin(NORDICS) & (df_questions["n_responses"] > 0)
]

# %%
shown = df_nordics_quest.drop_duplicates("question")[
    ["id", "question", "category"]
].reset_index(drop=True)
with pd.option_context("display.max_rows", None, "display.max_colwidth", None):
    display(
        shown.style.set_properties(
            subset=None, **{"text-align": "left"}
        ).set_table_styles([{"selector": "th", "props": [("text-align", "left")]}])
    )

# %% [markdown]
# ### Responses per question
#
# The number of respondents falls along the survey. Respondents skip
# questions. Partial responses stop early.

# %%
col_to_id = df_questions.drop_duplicates("col").set_index("col")["id"]
answered = df_nordics[col_to_id.index].notna().T.groupby(col_to_id, sort=False).any().T
answered = answered.loc[:, answered.any()]
counts_by_country = (
    answered.groupby(df_nordics["country"])
    .sum()
    .reset_index()
    .melt(id_vars="country", var_name="id", value_name="n_responses")
)
fig = px.bar(
    counts_by_country,
    x="id",
    y="n_responses",
    color="country",
    category_orders={"country": NORDICS, "id": list(answered.columns)},
    color_discrete_sequence=["#2a78d6", "#eb6834", "#1baf7a", "#eda100", "#e87ba4"],
    labels={"id": "Question id", "n_responses": "# Respondents", "country": "Country"},
    width=14 * answered.shape[1] + 250,
)
fig.update_traces(marker_line_color="#fcfcfb", marker_line_width=1)
fig.update_layout(
    plot_bgcolor="#fcfcfb", xaxis_tickangle=-90, xaxis_dtick=1, bargap=0.15
)
fig.show()

# %% [markdown]
# ## 3. Question types
#
# The codebook has one row for each response column and answer. It gives
# the question type, the answers and their order.

# %%
codebook = build_codebook(df_cols, df_raw)
codebook.head()

# %% [markdown]
# Each type has its own answer format and plot function:
#
# | Type | Answer format | Example | Plot function |
# | :-- | :-- | :-- | :-- |
# | `choice` | One or more options | `edu1`, `currentEmp13` | `plot_choice` |
# | `bool` | True or False | `rse1` | `plot_bool` |
# | `likert` | Share of time, 0% to 100% | `likert1` | `plot_likert`, `plot_likert2` |
# | `agreement` | Five levels, disagree to agree | `likert4b` | `plot_agreement` |
# | `text` | Free text | `edu2` | none |
# | `text_other` | Free text for the option "Other" | | none |
# | `empty` | No answers in the data | `org1cz` | none |
#
# A multiple-choice question has one column for each option. The table
# below counts the response columns of each type.

# %%
codebook.drop_duplicates("col")["type"].value_counts()

# %% [markdown]
# ### Single choice (type `choice`)

# %%
plot_choice(df_nordics, codebook, "edu1").show()

# %% [markdown]
# ### Multiple choice (type `choice`, one column per option)

# %%
plot_choice(df_nordics, codebook, "currentEmp13").show()

# %% [markdown]
# ### True or false (type `bool`)

# %%
plot_bool(df_nordics, codebook, "rse1").show()

# %% [markdown]
# ### Share of time (type `likert`)

# %%
plot_likert(df_nordics, codebook, "likert1").show()

# %% [markdown]
# ### Actual and desired share of time (`likert0` and `likert1`)

# %%
plot_likert2(df_nordics, codebook).show()

# %% [markdown]
# ### Agreement (type `agreement`)

# %%
plot_agreement(df_nordics, codebook, "likert4b").show()

# %% [markdown]
# ## 4. Group comparisons
#
# Each plot function has the argument `group_by`. It takes any column of the
# responses, e.g. `"age_group"` or `"country"`. The plots drop respondents
# without a group value.
#
# The example below uses three age groups: below 35, 35-45 and 45+.

# %%
df_nordics_age = add_age_group(df_nordics)
df_nordics_age["age_group"].value_counts(dropna=False)

# %%
plot_choice(df_nordics_age, codebook, "edu1", group_by="age_group").show()

# %%
plot_bool(df_nordics_age, codebook, "rse1", group_by="age_group").show()

# %%
plot_likert(df_nordics_age, codebook, "likert1", group_by="age_group").show()

# %%
plot_likert2(df_nordics_age, codebook, group_by="age_group").show()

# %%
plot_agreement(df_nordics_age, codebook, "likert4b", group_by="age_group").show()
