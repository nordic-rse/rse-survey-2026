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

# %%
import pandas as pd
import plotly.express as px
from IPython.display import display

from rse_survey_report.config import NORDICS
from rse_survey_report.utils import (
    get_counts_question_country,
    get_data_path,
    load_data,
    prepare_questions,
    preprocess_data,
)

# %%
path = get_data_path(file="2026_tf.csv", year=2026)
df_raw = load_data(path)
df_clean = preprocess_data(df_raw, excl_var="submitdate_0")
df_clean.head()

# %%
(
    df_clean.groupby("country")
    .agg(total=("complete", "size"), complete=("complete", "sum"))
    .assign(partial=lambda d: d["total"] - d["complete"])
    .sort_values(["total", "country"], ascending=[False, True])
    .head(n=20)
)


# %%
counts = get_counts_question_country(df_clean)
df_cols = load_data(get_data_path("2026_all_cols.csv", 2026))
df_questions = prepare_questions(df_cols, counts)

print(df_questions)

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
