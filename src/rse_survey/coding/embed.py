"""Embed tokens into a normalized vector space.

Clustering, centroid diagnostics and label proposal all need the same
"format inputs → encode → L2-normalized float matrix" step, so it lives here
once rather than being repeated at each call site.
"""

from __future__ import annotations

import numpy as np

from rse_survey.coding.models import get_embedder


def format_embed_texts(
    raw_texts: list[str],
    *,
    model_name: str,
    embed_prefix: str | None = None,
) -> list[str]:
    """Build embedding inputs.

    Use a *short* domain cue (``embed_prefix`` / chapter ``header``), not the full
    survey question. Prepending a long shared question makes every vector nearly
    identical and collapses clustering.
    """
    prefix = (embed_prefix or "").strip()
    if prefix:
        texts = [f"{prefix}: {t}" for t in raw_texts]
        print(f"Using short embed prefix: {prefix}")
    else:
        texts = list(raw_texts)
    if "e5" in model_name.lower():
        texts = [f"query: {t}" for t in texts]
    return texts


def embed_texts(
    raw_texts: list[str],
    *,
    model_name: str,
    embed_prefix: str | None = None,
    show_progress: bool = False,
) -> np.ndarray:
    """Encode tokens to an L2-normalized float matrix (rows align with input)."""
    texts = format_embed_texts(
        raw_texts, model_name=model_name, embed_prefix=embed_prefix
    )
    model = get_embedder(model_name)
    embeddings = model.encode(
        texts, show_progress_bar=show_progress, normalize_embeddings=True
    )
    return np.asarray(embeddings, dtype=float)
