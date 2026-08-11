"""Typed access to ``config/free_text_coding.yml`` (per-question coding params)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from rse_survey.config.paths import REPO_ROOT, resolve_repo_path
from rse_survey.config.yaml_io import read_yaml


def load_free_text_coding(
    path: str | Path | None = None,
    *,
    repo_root: Path | None = None,
) -> dict[str, Any]:
    root = repo_root or REPO_ROOT
    coding_path = resolve_repo_path(path or "config/free_text_coding.yml", root)
    if not coding_path.exists():
        return {}
    return read_yaml(coding_path)


def coding_config_path(path: str | Path | None = None) -> Path:
    return resolve_repo_path(path or "config/free_text_coding.yml")


def load_question_coding(
    question_id: str,
    *,
    coding_path: str | Path | None = None,
) -> tuple[dict[str, Any], Path]:
    """Load one question's coding settings from ``free_text_coding.yml``.

    Text always comes from the book-filtered survey table via ``text_column``
    (defaults to ``question_id``). ``data_path`` is not used.
    """
    path = coding_config_path(coding_path)
    all_cfgs = load_free_text_coding(path)
    if question_id not in all_cfgs:
        raise KeyError(
            f"Question {question_id!r} not found in {path}. "
            f"Known keys: {sorted(all_cfgs)}"
        )
    cfg = dict(all_cfgs[question_id] or {})
    if not isinstance(cfg, dict):
        raise ValueError(f"Coding entry for {question_id!r} must be a mapping: {path}")
    cfg["question_id"] = question_id
    cfg.setdefault("text_column", question_id)
    cfg.pop("data_path", None)  # legacy; text comes from focus-filtered tf
    method = str(cfg.get("cluster_method", "kmeans")).strip().lower()
    if method not in ("kmeans", "hdbscan"):
        raise ValueError(
            f"cluster_method must be 'kmeans' or 'hdbscan', got {method!r} "
            f"for {question_id}: {path}"
        )
    cfg["cluster_method"] = method
    if method == "kmeans" and "k" not in cfg:
        raise ValueError(
            f"cluster_method=kmeans requires 'k' for {question_id}: {path}"
        )
    return cfg, path
