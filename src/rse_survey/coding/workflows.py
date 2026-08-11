"""The three free-text coding runs, as plain functions.

``propose`` (cluster + draft labels), ``apply`` (broadcast reviewed labels)
and ``sample`` (inspect tokens per category). Prefect wraps these in
``flows/code_free_text.py``; keeping them Prefect-free keeps them testable.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pandas as pd

from rse_survey.coding.cluster import cluster_tokens
from rse_survey.coding.cluster_diagnostics import (
    cluster_centroid_diagnostics,
    cluster_similarity_report,
)
from rse_survey.coding.label import (
    apply_labels,
    collapse_same_label_clusters,
    labels_from_config,
    print_label_map,
    propose_labels,
    require_labels,
    save_labels_to_coding_yml,
)
from rse_survey.coding.seed_themes import apply_seed_themes, parse_seed_themes
from rse_survey.coding.token_labels import (
    TOKEN_LABELS_COLUMNS,
    TOKEN_LABELS_FILENAME,
    active_token_labels,
    print_tokens_per_cluster,
    read_token_labels_csv,
    token_labels_path,
    write_category_summary_from_labels,
    write_labeled_freezes,
)
from rse_survey.coding.tokenize import load_tokens
from rse_survey.config.book_config import BookConfig
from rse_survey.config.paths import REPO_ROOT, question_cache_dir
from rse_survey.data.clean_dataset import load_focus_frame


def run_sample_tokens(cfg: dict, n: int) -> None:
    question_id = cfg["question_id"]
    try:
        token_labels = read_token_labels_csv(question_id, include_excluded=True)
        active = active_token_labels(token_labels)
        n_excl = int(token_labels["exclude"].sum())
        print(
            f"\nToken samples from {TOKEN_LABELS_FILENAME} "
            f"(top {n} per category; exclude=1 omitted"
            + (f", {n_excl} excluded" if n_excl else "")
            + "):"
        )
        for cat, subset in active.groupby("category", sort=True):
            subset = subset.sort_values("n", ascending=False)
            examples = subset["token"].head(n).tolist()
            total = int(subset["n"].sum())
            print(
                f"\n=== {cat}  [weight={total}, {len(subset)} unique] ===\n"
                + ", ".join(examples)
            )
        print()
        return
    except FileNotFoundError:
        pass
    assign_path = question_cache_dir(question_id) / "cluster_assignments.csv"
    labels = require_labels(cfg)
    if not assign_path.exists():
        raise FileNotFoundError(
            f"Missing {assign_path}; run `rse-survey propose --question {question_id}` first."
        )
    assignments = pd.read_csv(assign_path)
    print_tokens_per_cluster(assignments, n=n, labels=labels)


def run_apply_labels_only(
    cfg: dict,
    *,
    coding_path: Path,
    sample_tokens: int | None = None,
    from_csv: bool = False,
) -> None:
    """Refresh coding outputs after human review.

    * Default: map YAML ``labels`` onto ``cluster_assignments.csv`` and rewrite
      ``token_labels.csv`` (use after renaming cluster categories in YAML).
    * ``from_csv=True``: keep manual token reallocations in ``token_labels.csv``
      and only refresh ``category_summary.csv`` (use after editing the CSV).
    """
    question_id = cfg["question_id"]
    out_dir = question_cache_dir(question_id)
    meta: dict[str, Any] = {}
    meta_path = out_dir / "meta.json"
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))

    if from_csv:
        token_labels = read_token_labels_csv(question_id, include_excluded=True)
        # Persist normalized exclude column back to disk
        token_labels[TOKEN_LABELS_COLUMNS].sort_values(
            ["exclude", "category_human", "token"], kind="mergesort"
        ).to_csv(token_labels_path(question_id), index=False)
        write_category_summary_from_labels(question_id, token_labels)
        active = active_token_labels(token_labels)
        # Keep legacy mirror of active tokens only
        legacy = active.rename(columns={"token": "raw"})
        legacy[["raw", "cluster_id", "category"]].to_csv(
            out_dir / "token_categories.csv", index=False
        )
        meta.update(
            {
                "csv_refreshed_at": datetime.now(UTC).isoformat(),
                "source_of_truth": TOKEN_LABELS_FILENAME,
                "question_id": question_id,
                "n_tokens": int(len(token_labels)),
                "n_excluded": int(token_labels["exclude"].sum()),
                "n_active": int(len(active)),
            }
        )
        with meta_path.open("w", encoding="utf-8") as f:
            json.dump(meta, f, indent=2)
        print(
            f"Refreshed category summary from edited {TOKEN_LABELS_FILENAME} "
            f"({len(active)} active / {len(token_labels)} total tokens, "
            f"{int(token_labels['exclude'].sum())} excluded, "
            f"{active['category'].nunique()} categories)"
        )
        if sample_tokens is not None:
            run_sample_tokens(cfg, sample_tokens)
        return

    assign_path = out_dir / "cluster_assignments.csv"
    labels = require_labels(cfg)
    if not assign_path.exists():
        raise FileNotFoundError(
            f"Missing {assign_path}; run `rse-survey propose --question {question_id}` first."
        )
    assignments = pd.read_csv(assign_path)
    categorized = apply_labels(assignments, labels)
    meta.update(
        {
            "labels_applied_at": datetime.now(UTC).isoformat(),
            "config": str(Path(coding_path).resolve().relative_to(REPO_ROOT)),
            "question_id": question_id,
            "source_of_truth": TOKEN_LABELS_FILENAME,
        }
    )
    write_labeled_freezes(question_id, assignments, categorized, meta)
    if sample_tokens is not None:
        print_tokens_per_cluster(assignments, n=sample_tokens, labels=labels)


def run_propose_labels(
    cfg: dict,
    *,
    coding_path: Path,
    book: BookConfig,
    sample_tokens: int | None = None,
    overwrite_labels: bool = False,
) -> None:
    existing = labels_from_config(cfg)
    if existing is not None and not overwrite_labels:
        raise RuntimeError(
            f"Labels already exist for {cfg['question_id']} in {coding_path}. "
            "Pass --overwrite-labels to replace them."
        )

    question_id = cfg["question_id"]
    cluster_method = str(cfg.get("cluster_method", "kmeans")).strip().lower()
    k = int(cfg["k"]) if "k" in cfg and cfg["k"] is not None else None
    model_name = cfg.get("model", "intfloat/e5-base-v2")
    random_state = int(cfg.get("random_state", 42))
    label_model = cfg.get("label_model", "Qwen/Qwen2.5-7B-Instruct")
    n_examples = int(cfg.get("n_examples", 12))
    label_load = str(cfg.get("label_load", "4bit"))
    embed_context = cfg.get("embed_context")
    if embed_context is not None:
        embed_context = str(embed_context).strip() or None
    # Short cue for embeddings only (full survey question collapses vectors)
    embed_prefix = cfg.get("embed_prefix")
    if embed_prefix is None:
        embed_prefix = cfg.get("header")
    if embed_prefix is not None:
        embed_prefix = str(embed_prefix).strip() or None
    min_cluster_size = int(cfg.get("min_cluster_size", 5))
    min_samples = cfg.get("min_samples")
    if min_samples is not None:
        min_samples = int(min_samples)
    umap_n_neighbors = int(cfg.get("umap_n_neighbors", 15))
    umap_n_components = int(cfg.get("umap_n_components", 5))
    umap_min_dist = float(cfg.get("umap_min_dist", 0.0))
    cluster_selection_method = (
        str(cfg.get("cluster_selection_method", "eom")).strip().lower()
    )
    if cluster_method == "hdbscan" and cluster_selection_method not in ("eom", "leaf"):
        raise ValueError(
            f"cluster_selection_method must be 'eom' or 'leaf', got "
            f"{cluster_selection_method!r} for {cfg['question_id']}"
        )
    assign_noise = bool(cfg.get("assign_noise", True))
    max_clusters = cfg.get("max_clusters")
    if max_clusters is not None:
        max_clusters = int(max_clusters)
    min_clusters = int(cfg.get("min_clusters", 2))
    merge_cosine = cfg.get("merge_cosine")
    if merge_cosine is not None:
        merge_cosine = float(merge_cosine)
    max_cluster_fraction = cfg.get("max_cluster_fraction")
    if max_cluster_fraction is not None:
        max_cluster_fraction = float(max_cluster_fraction)
    split_sub_k = int(cfg.get("split_sub_k", 3))
    seed_themes = parse_seed_themes(cfg)

    focus = load_focus_frame(book)
    n_focus_respondents = int(focus["row_id"].nunique()) if len(focus) else 0
    tokens = load_tokens(cfg, book=book)
    seeded = tokens.iloc[0:0].copy()
    residual = tokens
    seed_labels: dict[int, str] = {}
    if seed_themes:
        seeded, residual, seed_labels = apply_seed_themes(tokens, seed_themes)
    n_seeds = len(seed_labels)

    if residual.empty:
        if seeded.empty:
            raise ValueError(f"No tokens to cluster for {question_id}")
        assignments = seeded.copy()
        cluster_info = {
            "cluster_method": "seed_themes_only",
            "n_clusters": n_seeds,
            "n_noise": 0,
            "n_noise_assigned": 0,
            "noise_cluster_id": None,
            "k": None,
            "n_seed_themes": n_seeds,
            "seed_themes": list(seed_labels.values()),
        }
        proposed = dict(seed_labels)
        noise_id = None
    else:
        assignments_r, cluster_info = cluster_tokens(
            residual,
            model_name=model_name,
            random_state=random_state,
            cluster_method=cluster_method,
            k=k,
            embed_prefix=embed_prefix,
            min_cluster_size=min_cluster_size,
            min_samples=min_samples,
            umap_n_neighbors=umap_n_neighbors,
            umap_n_components=umap_n_components,
            umap_min_dist=umap_min_dist,
            cluster_selection_method=cluster_selection_method,
            assign_noise=assign_noise,
            max_clusters=max_clusters,
            min_clusters=min_clusters,
            merge_cosine=merge_cosine,
            max_cluster_fraction=max_cluster_fraction,
            split_sub_k=split_sub_k,
        )
        cluster_info["n_seed_themes"] = n_seeds
        cluster_info["seed_themes"] = list(seed_labels.values())

        cluster_similarity_report(
            assignments_r,
            model_name=model_name,
            embed_prefix=embed_prefix,
            noise_cluster_id=cluster_info.get("noise_cluster_id"),
        )
        cluster_centroid_diagnostics(
            assignments_r,
            model_name=model_name,
            embed_prefix=embed_prefix,
            noise_cluster_id=cluster_info.get("noise_cluster_id"),
        )

        meta_partial = {
            "question_id": question_id,
            "model": model_name,
            "embed_context": embed_context,
            "label_model": label_model,
            "label_load": label_load,
            "n_examples": n_examples,
            "random_state": random_state,
            "n_unique_tokens": int(len(assignments_r) + len(seeded)),
            "config": str(Path(coding_path).resolve().relative_to(REPO_ROOT)),
            "focus_countries": list(book.focus_countries),
            "focus_label": book.focus_label,
            "n_focus_respondents": n_focus_respondents,
            "created_at": datetime.now(UTC).isoformat(),
            **cluster_info,
        }
        # Label residual clusters only; seeds already have fixed names
        assignments_r, proposed_r, noise_id = propose_labels(
            assignments_r,
            label_model=label_model,
            n_examples=n_examples,
            seed=random_state,
            label_load=label_load,
            embed_context=embed_context,
            noise_cluster_id=cluster_info.get("noise_cluster_id"),
            model_name=model_name,
            embed_prefix=embed_prefix,
        )
        # Offset residual ids so they sit after seed theme ids
        if n_seeds:
            assignments_r = assignments_r.copy()
            assignments_r["cluster_id"] = (
                assignments_r["cluster_id"].astype(int) + n_seeds
            )
            proposed_r = {int(c) + n_seeds: name for c, name in proposed_r.items()}
            if noise_id is not None:
                noise_id = int(noise_id) + n_seeds
        assignments = (
            pd.concat([seeded, assignments_r], ignore_index=True)
            if n_seeds
            else assignments_r
        )
        proposed = {**seed_labels, **proposed_r}
        # Merge residual themes that duplicate a seed name (e.g. Prompt Engineering)
        assignments, proposed, noise_id = collapse_same_label_clusters(
            assignments, proposed, noise_cluster_id=noise_id
        )
        cluster_info["noise_cluster_id"] = noise_id
        cluster_info["n_clusters"] = int(assignments["cluster_id"].nunique()) - (
            1 if noise_id is not None else 0
        )
        meta = meta_partial
        meta.update(cluster_info)
        meta["n_unique_tokens"] = int(len(assignments))
        print_label_map(proposed)
        save_labels_to_coding_yml(question_id, proposed, coding_path=coding_path)
        categorized = apply_labels(assignments, proposed)
        meta["labels_applied_at"] = datetime.now(UTC).isoformat()
        write_labeled_freezes(question_id, assignments, categorized, meta)
        if sample_tokens is not None:
            print_tokens_per_cluster(assignments, n=sample_tokens, labels=proposed)
        return

    # seeds-only path
    meta = {
        "question_id": question_id,
        "model": model_name,
        "embed_context": embed_context,
        "label_model": label_model,
        "label_load": label_load,
        "n_examples": n_examples,
        "random_state": random_state,
        "n_unique_tokens": int(len(assignments)),
        "config": str(Path(coding_path).resolve().relative_to(REPO_ROOT)),
        "focus_countries": list(book.focus_countries),
        "focus_label": book.focus_label,
        "n_focus_respondents": n_focus_respondents,
        "created_at": datetime.now(UTC).isoformat(),
        **cluster_info,
    }
    print_label_map(proposed)
    save_labels_to_coding_yml(question_id, proposed, coding_path=coding_path)
    categorized = apply_labels(assignments, proposed)
    meta["labels_applied_at"] = datetime.now(UTC).isoformat()
    write_labeled_freezes(question_id, assignments, categorized, meta)
    if sample_tokens is not None:
        print_tokens_per_cluster(assignments, n=sample_tokens, labels=proposed)
    return
