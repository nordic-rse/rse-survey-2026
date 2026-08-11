"""Report how separable the clusters actually are.

Run before labelling: if two centroids sit at cosine >~0.85 the *clustering*
merged their content, and no prompt wording will make their labels distinct.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from rse_survey.coding.cluster import weighted_centroids
from rse_survey.coding.embed import embed_texts


def cluster_similarity_report(
    assignments: pd.DataFrame,
    *,
    model_name: str,
    embed_prefix: str | None = None,
    noise_cluster_id: int | None = None,
) -> None:
    """Full pairwise centroid similarity: matrix + per-cluster mean + histogram.

    Distinguishes "one hub cluster sits near everyone" (high mean similarity
    concentrated in one row) from "general embedding collapse" (uniformly
    high similarity everywhere) from "a couple of real near-duplicate pairs"
    (a few outlier-high entries, rest are unremarkable).
    """
    emb = embed_texts(
        assignments["raw"].tolist(), model_name=model_name, embed_prefix=embed_prefix
    )
    ids = assignments["cluster_id"].to_numpy(dtype=int)
    weights = (
        assignments["n"].to_numpy(dtype=float) if "n" in assignments.columns else None
    )
    cluster_list, cents = weighted_centroids(
        emb, ids, weights, exclude_id=noise_cluster_id
    )

    sims = cents @ cents.T
    np.fill_diagonal(sims, np.nan)

    print("\nFull centroid similarity matrix:")
    header = "      " + " ".join(f"c{c:<5}" for c in cluster_list)
    print(header)
    for i, c in enumerate(cluster_list):
        row = " ".join(
            "  -   " if np.isnan(sims[i, j]) else f"{sims[i, j]:.3f} "
            for j in range(len(cluster_list))
        )
        print(f"c{c:<4} {row}")

    off_diag = sims[~np.isnan(sims)]
    print(
        f"\nOff-diagonal similarity: mean={off_diag.mean():.3f}, "
        f"min={off_diag.min():.3f}, max={off_diag.max():.3f}"
    )

    print("\nPer-cluster mean similarity to all others (high = 'hub'):")
    for i, c in enumerate(cluster_list):
        row_mean = np.nanmean(sims[i, :])
        print(f"  cluster {c}: {row_mean:.3f}")
    print()


def cluster_centroid_diagnostics(
    assignments: pd.DataFrame,
    *,
    model_name: str,
    embed_prefix: str | None = None,
    noise_cluster_id: int | None = None,
    top_n: int = 5,
) -> None:
    """Print the most similar cluster centroid pairs (cosine).

    High similarity (>~0.85) between two clusters means the *clustering* put
    them close together in embedding space — no prompt engineering will make
    their labels feel distinct, because the content genuinely overlaps. Use
    this to decide whether to lower merge_cosine / raise min_cluster_size
    instead of fighting it at the labeling stage.
    """
    emb = embed_texts(
        assignments["raw"].tolist(), model_name=model_name, embed_prefix=embed_prefix
    )
    ids = assignments["cluster_id"].to_numpy(dtype=int)
    weights = (
        assignments["n"].to_numpy(dtype=float) if "n" in assignments.columns else None
    )
    cluster_list, cents = weighted_centroids(
        emb, ids, weights, exclude_id=noise_cluster_id
    )
    sims = cents @ cents.T
    pairs = sorted(
        (
            (sims[i, j], cluster_list[i], cluster_list[j])
            for i in range(len(cluster_list))
            for j in range(i + 1, len(cluster_list))
        ),
        reverse=True,
    )
    print(f"\nMost similar cluster pairs (top {top_n}, cosine of weighted centroids):")
    for sim, a, b in pairs[:top_n]:
        print(f"  cluster {a} vs cluster {b}: {sim:.3f}")
    print()
