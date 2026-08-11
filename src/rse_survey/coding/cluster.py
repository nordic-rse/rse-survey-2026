"""Group tokens into candidate themes.

Two methods: ``kmeans`` (fixed k) and ``hdbscan`` (density-based, over a UMAP
projection). Both feed the same post-processing — reassign noise, merge
near-duplicate centroids, split any cluster that swallowed the dataset.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from rse_survey.coding.embed import embed_texts


def _remap_hdbscan_labels(raw_labels: np.ndarray) -> tuple[np.ndarray, int | None, int]:
    """Map HDBSCAN labels to contiguous ids 0..n-1; noise (-1) → last id.

    Returns ``(remapped, noise_cluster_id_or_None, n_noise)``.
    """
    raw_labels = np.asarray(raw_labels)
    n_noise = int((raw_labels == -1).sum())
    clustered = sorted({int(x) for x in raw_labels.tolist() if int(x) != -1})
    mapping = {old: new for new, old in enumerate(clustered)}
    noise_id: int | None = None
    if n_noise:
        noise_id = len(clustered)
        mapping[-1] = noise_id
    remapped = np.array([mapping[int(x)] for x in raw_labels], dtype=int)
    return remapped, noise_id, n_noise


def weighted_centroids(
    embeddings: np.ndarray,
    cluster_ids: np.ndarray,
    weights: np.ndarray | None,
    *,
    exclude_id: int | None = None,
) -> tuple[list[int], np.ndarray]:
    """Return ``(ids, centroid_matrix)`` for non-excluded clusters."""
    ids = sorted(
        {
            int(x)
            for x in cluster_ids.tolist()
            if exclude_id is None or int(x) != exclude_id
        }
    )
    if not ids:
        return [], np.zeros((0, embeddings.shape[1]), dtype=float)
    w = (
        np.ones(len(cluster_ids), dtype=float)
        if weights is None
        else np.asarray(weights, dtype=float)
    )
    cents = []
    for cid in ids:
        mask = cluster_ids == cid
        ww = w[mask]
        ww = ww / ww.sum() if ww.sum() > 0 else np.full(ww.shape, 1.0 / len(ww))
        c = (embeddings[mask] * ww[:, None]).sum(axis=0)
        norm = np.linalg.norm(c)
        cents.append(c / norm if norm > 0 else c)
    return ids, np.vstack(cents)


def _assign_noise_to_nearest(
    embeddings: np.ndarray,
    cluster_ids: np.ndarray,
    *,
    noise_cluster_id: int,
    weights: np.ndarray | None = None,
) -> tuple[np.ndarray, int]:
    """Reassign Unclustered points to the nearest non-noise centroid (cosine)."""
    labels = np.asarray(cluster_ids, dtype=int).copy()
    ids, cents = weighted_centroids(
        embeddings, labels, weights, exclude_id=noise_cluster_id
    )
    if not ids:
        return labels, 0
    noise_mask = labels == noise_cluster_id
    n_noise = int(noise_mask.sum())
    if n_noise == 0:
        return labels, 0
    noise_vecs = embeddings[noise_mask]
    # embeddings are L2-normalized; centroids are too
    sims = noise_vecs @ cents.T
    nearest = sims.argmax(axis=1)
    labels[noise_mask] = np.array(ids, dtype=int)[nearest]
    print(f"Assigned {n_noise} Unclustered token(s) to nearest theme centroid")
    return labels, n_noise


def _merge_clusters_by_centroid(
    embeddings: np.ndarray,
    cluster_ids: np.ndarray,
    *,
    weights: np.ndarray | None = None,
    noise_cluster_id: int | None = None,
    max_clusters: int | None = None,
    min_clusters: int = 2,
    merge_cosine: float | None = None,
) -> tuple[np.ndarray, int | None]:
    """Merge non-noise clusters by centroid cosine similarity.

    Phase A (soft): merge while best similarity ≥ ``merge_cosine`` **and**
    the number of themes stays above ``min_clusters``.
    Phase B (hard cap): if still above ``max_clusters``, merge nearest pairs
    until the cap is met (ignores cosine threshold).

    ``Unclustered`` (``noise_cluster_id``) is never merged into.
    """
    labels = np.asarray(cluster_ids, dtype=int).copy()
    if max_clusters is None and merge_cosine is None:
        return labels, noise_cluster_id

    min_clusters = max(2, int(min_clusters))
    if max_clusters is not None and max_clusters < min_clusters:
        raise ValueError(
            f"max_clusters ({max_clusters}) must be >= min_clusters ({min_clusters})"
        )

    def theme_count() -> int:
        return len(
            {
                int(x)
                for x in labels.tolist()
                if noise_cluster_id is None or int(x) != noise_cluster_id
            }
        )

    def merge_best_pair() -> float | None:
        ids, cents = weighted_centroids(
            embeddings, labels, weights, exclude_id=noise_cluster_id
        )
        if len(ids) <= 1:
            return None
        sims = cents @ cents.T
        np.fill_diagonal(sims, -np.inf)
        flat = int(np.argmax(sims))
        i, j = divmod(flat, sims.shape[0])
        best = float(sims[i, j])
        a, b = ids[i], ids[j]
        keep, drop = (a, b) if a < b else (b, a)
        labels[labels == drop] = keep
        return best

    n_before = theme_count()
    soft_merges = 0
    hard_merges = 0

    # Phase A: soft near-duplicate merges, never below min_clusters
    if merge_cosine is not None:
        while theme_count() > min_clusters:
            ids, cents = weighted_centroids(
                embeddings, labels, weights, exclude_id=noise_cluster_id
            )
            if len(ids) <= 1:
                break
            sims = cents @ cents.T
            np.fill_diagonal(sims, -np.inf)
            best = float(sims.max())
            if best < merge_cosine:
                break
            merge_best_pair()
            soft_merges += 1

    # Phase B: hard codebook cap
    if max_clusters is not None:
        while theme_count() > max_clusters:
            if merge_best_pair() is None:
                break
            hard_merges += 1

    non_noise = sorted(
        {
            int(x)
            for x in labels.tolist()
            if noise_cluster_id is None or int(x) != noise_cluster_id
        }
    )
    mapping = {old: new for new, old in enumerate(non_noise)}
    new_noise: int | None = None
    if noise_cluster_id is not None and (labels == noise_cluster_id).any():
        new_noise = len(non_noise)
        mapping[int(noise_cluster_id)] = new_noise
    remapped = np.array([mapping[int(x)] for x in labels], dtype=int)
    n_after = len(non_noise)
    if soft_merges or hard_merges:
        print(
            f"Merged centroids {n_before} → {n_after} clusters "
            f"(soft={soft_merges} at cosine≥{merge_cosine}, "
            f"hard={hard_merges} to max_clusters={max_clusters}; "
            f"floor min_clusters={min_clusters})"
        )
    return remapped, new_noise


def _cluster_kmeans(embeddings: np.ndarray, *, k: int, random_state: int) -> np.ndarray:
    from sklearn.cluster import KMeans

    print(f"Clustering with KMeans(k={k}) …")
    km = KMeans(n_clusters=k, random_state=random_state, n_init=10)
    return km.fit_predict(embeddings).astype(int)


def _split_oversized_clusters(
    embeddings: np.ndarray,
    cluster_ids: np.ndarray,
    *,
    weights: np.ndarray | None = None,
    max_fraction: float = 0.30,
    sub_k: int = 3,
    random_state: int = 42,
    exclude_id: int | None = None,
) -> np.ndarray:
    """Re-run KMeans on any cluster holding more than ``max_fraction`` of the
    total weight, splitting it into ``sub_k`` sub-clusters appended as new
    ids. A blunt but reliable fallback for when HDBSCAN's cluster-selection
    method leaves one dominant, under-differentiated cluster regardless of
    parameter tuning.

    ``exclude_id`` (typically the Unclustered/noise bucket) is never split.
    """
    from sklearn.cluster import KMeans

    labels = np.asarray(cluster_ids, dtype=int).copy()
    w = np.ones(len(labels)) if weights is None else np.asarray(weights, dtype=float)
    total = w.sum()
    next_id = labels.max() + 1

    for cid in sorted(set(labels.tolist())):
        if exclude_id is not None and cid == exclude_id:
            continue
        mask = labels == cid
        frac = w[mask].sum() / total
        if frac <= max_fraction or mask.sum() < sub_k * 2:
            continue
        print(f"  cluster {cid} is {100 * frac:.0f}% of data — splitting into {sub_k}")
        sub_emb = embeddings[mask]
        sub_labels = KMeans(
            n_clusters=sub_k, random_state=random_state, n_init=10
        ).fit_predict(sub_emb)
        new_ids = np.where(sub_labels == 0, cid, next_id + sub_labels - 1)
        labels[mask] = new_ids
        next_id += sub_k - 1
    return labels


def _cluster_umap_hdbscan(
    embeddings: np.ndarray,
    *,
    random_state: int,
    min_cluster_size: int = 5,
    min_samples: int | None = None,
    umap_n_neighbors: int = 15,
    umap_n_components: int = 5,
    umap_min_dist: float = 0.0,
    cluster_selection_method: str = "eom",
) -> tuple[np.ndarray, int | None, int]:
    try:
        import hdbscan
        import umap
    except ImportError as exc:
        raise ImportError(
            "cluster_method=hdbscan requires the 'umap-learn' and 'hdbscan' "
            "packages (install with: uv sync --extra hf)"
        ) from exc

    n = embeddings.shape[0]
    if n < 3:
        raise ValueError(f"Need at least 3 tokens for UMAP+HDBSCAN; got {n}")

    n_neighbors = min(umap_n_neighbors, max(2, n - 1))
    n_components = min(umap_n_components, max(2, n - 1), 100)
    if min_cluster_size < 2:
        raise ValueError("min_cluster_size must be >= 2")
    if min_cluster_size > n:
        raise ValueError(
            f"min_cluster_size={min_cluster_size} exceeds n_tokens={n}; lower it"
        )

    print(
        f"Reducing with UMAP(n_neighbors={n_neighbors}, "
        f"n_components={n_components}, min_dist={umap_min_dist}) …"
    )
    reducer = umap.UMAP(
        n_neighbors=n_neighbors,
        n_components=n_components,
        min_dist=umap_min_dist,
        metric="cosine",
        random_state=random_state,
    )
    reduced = reducer.fit_transform(embeddings)

    hdbscan_kwargs: dict[str, Any] = {
        "min_cluster_size": min_cluster_size,
        "metric": "euclidean",
        "cluster_selection_method": cluster_selection_method,
    }
    if min_samples is not None:
        hdbscan_kwargs["min_samples"] = int(min_samples)

    print(
        f"Clustering with HDBSCAN(min_cluster_size={min_cluster_size}"
        + (f", min_samples={min_samples}" if min_samples is not None else "")
        + f", cluster_selection_method={cluster_selection_method}"
        + ") …"
    )
    clusterer = hdbscan.HDBSCAN(**hdbscan_kwargs)
    raw = clusterer.fit_predict(reduced)
    remapped, noise_id, n_noise = _remap_hdbscan_labels(raw)
    n_found = len(
        {int(x) for x in remapped.tolist() if noise_id is None or int(x) != noise_id}
    )
    print(
        f"HDBSCAN found {n_found} cluster(s); "
        f"{n_noise} token(s) marked Unclustered"
        + (f" (cluster_id={noise_id})" if noise_id is not None else "")
    )
    if n_found == 0:
        raise RuntimeError(
            "HDBSCAN found no clusters (everything is noise). "
            "Try lowering min_cluster_size or min_samples."
        )

    return remapped, noise_id, n_noise


def cluster_tokens(
    tokens: pd.DataFrame,
    *,
    model_name: str,
    random_state: int,
    cluster_method: str = "kmeans",
    k: int | None = None,
    embed_prefix: str | None = None,
    min_cluster_size: int = 5,
    min_samples: int | None = None,
    umap_n_neighbors: int = 15,
    umap_n_components: int = 5,
    umap_min_dist: float = 0.0,
    cluster_selection_method: str = "eom",
    assign_noise: bool = True,
    max_clusters: int | None = None,
    min_clusters: int = 2,
    merge_cosine: float | None = None,
    max_cluster_fraction: float | None = None,
    split_sub_k: int = 3,
) -> tuple[pd.DataFrame, dict[str, Any]]:
    """Embed tokens and cluster. Returns ``(assignments, cluster_info)``."""
    print(f"Embedding {len(tokens)} unique tokens …")
    embeddings = embed_texts(
        tokens["raw"].tolist(),
        model_name=model_name,
        embed_prefix=embed_prefix,
        show_progress=True,
    )
    weights = tokens["n"].to_numpy(dtype=float) if "n" in tokens.columns else None

    noise_cluster_id: int | None = None
    n_noise = 0
    n_noise_assigned = 0
    method = cluster_method.strip().lower()
    if method == "kmeans":
        if k is None:
            raise ValueError("k is required when cluster_method=kmeans")
        cluster_ids = _cluster_kmeans(embeddings, k=k, random_state=random_state)
    elif method == "hdbscan":
        cluster_ids, noise_cluster_id, n_noise = _cluster_umap_hdbscan(
            embeddings,
            random_state=random_state,
            min_cluster_size=min_cluster_size,
            min_samples=min_samples,
            umap_n_neighbors=umap_n_neighbors,
            umap_n_components=umap_n_components,
            umap_min_dist=umap_min_dist,
            cluster_selection_method=cluster_selection_method,
        )
        if assign_noise and noise_cluster_id is not None:
            cluster_ids, n_noise_assigned = _assign_noise_to_nearest(
                embeddings,
                cluster_ids,
                noise_cluster_id=noise_cluster_id,
                weights=weights,
            )
            noise_cluster_id = None
            n_noise = 0
    else:
        raise ValueError(f"Unknown cluster_method={cluster_method!r}")

    if max_clusters is not None or merge_cosine is not None:
        cluster_ids, noise_cluster_id = _merge_clusters_by_centroid(
            embeddings,
            cluster_ids,
            weights=weights,
            noise_cluster_id=noise_cluster_id,
            max_clusters=max_clusters,
            min_clusters=min_clusters,
            merge_cosine=merge_cosine,
        )

    n_splits = 0
    if max_cluster_fraction is not None:
        before_ids = set(cluster_ids.tolist())
        cluster_ids = _split_oversized_clusters(
            embeddings,
            cluster_ids,
            weights=weights,
            max_fraction=max_cluster_fraction,
            sub_k=split_sub_k,
            random_state=random_state,
            exclude_id=noise_cluster_id,
        )
        n_splits = len(set(cluster_ids.tolist())) - len(before_ids)
        if n_splits:
            # Renumber to stay contiguous 0..n-1; noise_cluster_id may shift.
            unique_ids = sorted(set(cluster_ids.tolist()))
            remap = {old: new for new, old in enumerate(unique_ids)}
            cluster_ids = np.array([remap[int(x)] for x in cluster_ids], dtype=int)
            if noise_cluster_id is not None:
                noise_cluster_id = remap.get(noise_cluster_id, noise_cluster_id)

    out = tokens.copy()
    out["cluster_id"] = cluster_ids.astype(int)
    n_theme = int(out["cluster_id"].nunique()) - (
        1 if noise_cluster_id is not None else 0
    )
    sizes = (
        out.groupby("cluster_id")["n"].sum()
        if "n" in out.columns
        else out.groupby("cluster_id").size()
    )
    print(
        f"Final codebook: {n_theme} theme(s)"
        + (" + Unclustered" if noise_cluster_id is not None else "")
        + f"; sizes (weight) = {dict(sorted((int(i), int(v)) for i, v in sizes.items()))}"
    )
    info: dict[str, Any] = {
        "cluster_method": method,
        "n_clusters": n_theme,
        "n_noise": n_noise,
        "n_noise_assigned": n_noise_assigned,
        "noise_cluster_id": noise_cluster_id,
        "k": k,
        "embed_prefix": embed_prefix,
        "assign_noise": assign_noise if method == "hdbscan" else None,
        "min_cluster_size": min_cluster_size if method == "hdbscan" else None,
        "min_samples": min_samples if method == "hdbscan" else None,
        "umap_n_neighbors": umap_n_neighbors if method == "hdbscan" else None,
        "umap_n_components": umap_n_components if method == "hdbscan" else None,
        "umap_min_dist": umap_min_dist if method == "hdbscan" else None,
        "cluster_selection_method": cluster_selection_method
        if method == "hdbscan"
        else None,
        "max_clusters": max_clusters,
        "min_clusters": min_clusters,
        "merge_cosine": merge_cosine,
        "max_cluster_fraction": max_cluster_fraction,
        "split_sub_k": split_sub_k if max_cluster_fraction is not None else None,
        "n_oversized_splits": n_splits,
    }
    return out, info
