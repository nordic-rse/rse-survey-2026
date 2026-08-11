"""Name each cluster, in English, with an instruction-tuned LLM.

Also handles the two failure modes that follow from multilingual answers:
clusters that split by language, and labels that restate an existing theme.
"""

from __future__ import annotations

import re
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

from rse_survey.coding.cluster import weighted_centroids
from rse_survey.coding.embed import embed_texts
from rse_survey.coding.models import get_labeler


def labels_from_config(cfg: dict) -> dict[int, str] | None:
    raw = cfg.get("labels")
    if raw is None:
        return None
    if not isinstance(raw, dict) or not raw:
        raise ValueError(
            "Config 'labels' must be a non-empty mapping of cluster_id → name"
        )
    return {int(k): str(v) for k, v in raw.items()}


def require_labels(cfg: dict) -> dict[int, str]:
    labels = labels_from_config(cfg)
    if labels is None:
        raise ValueError(
            "Config is missing 'labels'. Run `rse-survey propose --question …` "
            "first (or add a labels map by hand), then retry."
        )
    return labels


def save_labels_to_coding_yml(
    question_id: str,
    labels: dict[int, str],
    *,
    coding_path: Path,
) -> None:
    """Update ``labels:`` under ``question_id`` in ``free_text_coding.yml``."""
    path = Path(coding_path)
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        raise ValueError(f"Coding config must be a mapping: {path}")
    entry = dict(raw.get(question_id) or {})
    entry["labels"] = {int(k): str(v) for k, v in sorted(labels.items())}
    # Drop redundant / legacy keys from the written entry
    entry.pop("question_id", None)
    entry.pop("data_path", None)
    raw[question_id] = entry
    header = (
        "# HF free-text coding configs keyed by question_id.\n"
        "# Text comes from the book-filtered survey table (text_column / question id).\n"
        "# propose/apply update the labels: map under each key.\n\n"
    )
    body = yaml.safe_dump(
        raw,
        sort_keys=False,
        allow_unicode=True,
        default_flow_style=False,
        width=100,
    )
    path.write_text(header + body, encoding="utf-8")
    print(f"Wrote labels for {question_id} to {path}")


def print_label_map(labels: dict[int, str]) -> None:
    print("\nProposed labels (cluster_id → name):")
    for cid in sorted(labels):
        print(f"  {cid}: {labels[cid]}")
    print()


def apply_labels(assignments: pd.DataFrame, labels: dict[int, str]) -> pd.DataFrame:
    missing = sorted(set(assignments["cluster_id"].astype(int)) - set(labels))
    if missing:
        raise ValueError(
            f"Config labels missing cluster_id(s): {missing}. "
            "Add them to the YAML labels map."
        )
    out = assignments.copy()
    out["cluster_id"] = out["cluster_id"].astype(int)
    out["category"] = out["cluster_id"].map(labels)
    if "n" not in out.columns:
        out["n"] = 1
    return out[["raw", "cluster_id", "category", "n"]]


def _top_examples(
    assignments: pd.DataFrame,
    cluster_id: int,
    n: int,
) -> list[str]:
    """Most frequent unique raw tokens in a cluster."""
    subset = assignments.loc[assignments["cluster_id"] == cluster_id].dropna(
        subset=["raw"]
    )
    if subset.empty:
        return []
    df = subset.copy()
    df["raw"] = df["raw"].astype(str)
    if "n" in df.columns:
        df = df.sort_values("n", ascending=False).drop_duplicates(
            subset=["raw"], keep="first"
        )
    else:
        df = df.drop_duplicates(subset=["raw"])
    return df["raw"].head(n).tolist()


def _normalize_label(label: str) -> str:
    return re.sub(r"\s+", " ", label.strip().casefold())


def _labels_conflict(a: str, b: str) -> bool:
    """True if labels are the same or one is a trivial variant of the other."""
    na, nb = _normalize_label(a), _normalize_label(b)
    if not na or not nb:
        return False
    if na == nb:
        return True
    if na in nb or nb in na:
        return True
    return False


_VAGUE_LABELS = frozenset(
    {
        "skill set",
        "skills",
        "general skills",
        "various skills",
        "mixed skills",
        "abilities",
        "competencies",
        "competences",
        "miscellaneous",
        "various",
        "general",
        "other",
        "empty cluster",
    }
)


def _is_vague_label(label: str) -> bool:
    return _normalize_label(label) in _VAGUE_LABELS


def collapse_same_label_clusters(
    assignments: pd.DataFrame,
    labels: dict[int, str],
    *,
    noise_cluster_id: int | None = None,
) -> tuple[pd.DataFrame, dict[int, str], int | None]:
    """Merge clusters that share the same (normalized) category name.

    Used when multilingual answers split into language-specific clusters that
    the labeler correctly names with the same English theme.
    """
    theme_labels = {
        cid: name
        for cid, name in labels.items()
        if noise_cluster_id is None or int(cid) != int(noise_cluster_id)
    }
    groups: dict[str, list[int]] = {}
    for cid, name in theme_labels.items():
        groups.setdefault(_normalize_label(name), []).append(int(cid))

    merge_map: dict[int, int] = {}
    for members in groups.values():
        keep = min(members)
        for cid in members:
            merge_map[cid] = keep

    if noise_cluster_id is not None:
        merge_map[int(noise_cluster_id)] = int(noise_cluster_id)

    out = assignments.copy()
    out["cluster_id"] = out["cluster_id"].map(lambda x: merge_map[int(x)])

    # Remap to contiguous ids; noise last
    non_noise = sorted(
        {
            int(x)
            for x in out["cluster_id"].tolist()
            if noise_cluster_id is None or int(x) != int(noise_cluster_id)
        }
    )
    remap = {old: new for new, old in enumerate(non_noise)}
    new_noise: int | None = None
    if noise_cluster_id is not None and (out["cluster_id"] == noise_cluster_id).any():
        new_noise = len(non_noise)
        remap[int(noise_cluster_id)] = new_noise
    out["cluster_id"] = out["cluster_id"].map(lambda x: remap[int(x)])

    # Canonical English name = first label that mapped into each keep id
    name_for_old = {cid: theme_labels[cid] for cid in theme_labels}
    new_labels: dict[int, str] = {}
    for old_keep, new_id in remap.items():
        if new_noise is not None and new_id == new_noise:
            new_labels[new_id] = "Unclustered"
            continue
        # Prefer shortest Title-Case English name among merged members
        candidates = [
            name_for_old[old]
            for old, keep in merge_map.items()
            if keep == old_keep and old in name_for_old
        ]
        new_labels[new_id] = (
            sorted(candidates, key=len)[0] if candidates else f"Cluster {new_id}"
        )

    n_before = len(theme_labels)
    n_after = len(non_noise)
    if n_after < n_before:
        print(
            f"Collapsed {n_before - n_after} duplicate-theme cluster(s) "
            f"by shared English label ({n_before} → {n_after})"
        )
    return out, new_labels, new_noise


def propose_labels(
    assignments: pd.DataFrame,
    *,
    label_model: str,
    n_examples: int = 12,
    seed: int = 0,
    label_load: str = "4bit",
    embed_context: str | None = None,
    noise_cluster_id: int | None = None,
    model_name: str | None = None,
    embed_prefix: str | None = None,
    n_contrast: int = 8,
) -> tuple[pd.DataFrame, dict[int, str], int | None]:
    """Draft English category names; merge translation-split clusters.

    Returns ``(assignments, labels, noise_cluster_id)`` — assignments may be
    remapped when two clusters receive the same theme name (e.g. English
    "Critical Thinking" and Spanish "pensamiento crítico").
    """
    from tqdm import tqdm

    labeler = get_labeler(label_model, label_load=label_load)
    proposed: dict[int, str] = {}

    question_note = ""
    ctx = (embed_context or "").strip()
    if ctx:
        question_note = (
            f'The survey question was:\n"{ctx}"\n\n'
            "Labels should reflect themes in answers to that question.\n\n"
        )

    system_prompt = (
        "You are labeling clusters produced by an automated survey-coding "
        "pipeline. Answers may be in English, German, Spanish, or mixed.\n\n"
        f"{question_note}"
        "Name the shared theme of THIS cluster in English.\n\n"
        "Rules:\n"
        "- Output ONLY the label. No preamble, no explanation, no quotes.\n"
        "- English only — never put German/Spanish words or translations in "
        "the label (no parentheses).\n"
        "- 1 to 5 words, Title Case, no trailing punctuation.\n"
        "- Do not copy an answer verbatim.\n"
        "- Prefer the angle that distinguishes THIS cluster from a nearby one.\n"
        "- If THIS cluster is clearly the same theme as an already-used label "
        "(including a translation of it), reuse that exact English label.\n"
        "- Never invent a near-duplicate of an already-used label.\n"
        "- Avoid vague labels: Skill Set, Skills, Abilities, Competencies.\n"
        "- If THIS cluster is a mixed grab-bag with no clear theme, output "
        "'Mixed / Unclear'.\n"
        "- Never output 'Miscellaneous', 'Various', 'General', or 'Other'."
    )

    few_shot = [
        {
            "role": "user",
            "content": (
                "THIS cluster: rust, python, learn rust, programming in python\n"
                "NEARBY cluster (different theme): unit testing, pytest, tdd\n"
                "Label:"
            ),
        },
        {"role": "assistant", "content": "Programming Languages"},
        {
            "role": "user",
            "content": (
                "Already used labels: Critical Thinking\n"
                "THIS cluster: pensamiento crítico, escepticismo saludable, "
                "vorwissen um die ergebnisse beurteilen zu können\n"
                "Label:"
            ),
        },
        {"role": "assistant", "content": "Critical Thinking"},
        {
            "role": "user",
            "content": (
                "Already used labels: Programming Languages\n"
                "THIS cluster: unit testing, pytest, tdd, test coverage\n"
                "NEARBY cluster (different theme): rust, python\n"
                "Label:"
            ),
        },
        {"role": "assistant", "content": "Software Testing"},
        {
            "role": "user",
            "content": "THIS cluster: blue, tuesday, my cat, running late\nLabel:",
        },
        {"role": "assistant", "content": "Mixed / Unclear"},
    ]

    cluster_ids = sorted(
        int(x)
        for x in assignments["cluster_id"].dropna().unique()
        if noise_cluster_id is None or int(x) != noise_cluster_id
    )
    used_labels: list[str] = []

    nearest: dict[int, int] = {}
    if model_name and len(cluster_ids) >= 2:
        emb = embed_texts(
            assignments["raw"].astype(str).tolist(),
            model_name=model_name,
            embed_prefix=embed_prefix,
        )
        weights = (
            assignments["n"].to_numpy(dtype=float)
            if "n" in assignments.columns
            else None
        )
        ids, cents = weighted_centroids(
            emb,
            assignments["cluster_id"].to_numpy(dtype=int),
            weights,
            exclude_id=noise_cluster_id,
        )
        if len(ids) >= 2:
            sims = cents @ cents.T
            np.fill_diagonal(sims, -np.inf)
            for i, cid in enumerate(ids):
                nearest[int(cid)] = int(ids[int(np.argmax(sims[i]))])

    def _generate(user: str) -> str:
        messages = (
            [{"role": "system", "content": system_prompt}]
            + few_shot
            + [{"role": "user", "content": user}]
        )
        out = labeler(
            messages,
            return_full_text=False,
            max_new_tokens=16,
            do_sample=False,
        )
        text = out[0]["generated_text"]
        if isinstance(text, list):
            text = text[-1].get("content", str(text))
        return str(text).strip().split("\n")[0].strip().strip('"').strip("'")

    if noise_cluster_id is not None:
        proposed[int(noise_cluster_id)] = "Unclustered"

    for c in tqdm(cluster_ids, desc="Proposing labels", unit="cluster"):
        examples = _top_examples(assignments, c, n_examples)
        if not examples:
            proposed[c] = "Empty cluster"
            tqdm.write(f"  cluster {c}: {proposed[c]}")
            continue

        parts = [f"THIS cluster: {', '.join(examples)}"]
        nb = nearest.get(c)
        if nb is not None:
            other = _top_examples(assignments, nb, n_contrast)
            if other:
                parts.append(
                    "NEARBY cluster (different theme — do not name this): "
                    + ", ".join(other)
                )
        if used_labels:
            parts.insert(
                0,
                "Already used labels: " + "; ".join(used_labels),
            )
        parts.append("Label:")
        user = "\n".join(parts)

        label = _generate(user)

        # Reject vague names once
        if _is_vague_label(label):
            label = _generate(
                "That label is too vague. Name a concrete theme.\n" + user
            )

        # Same theme as an existing label (incl. translation) → reuse it
        matched = next((u for u in used_labels if _labels_conflict(label, u)), None)
        if matched is not None:
            # One retry asking for a *different* theme; if still same, merge
            retry = _generate(
                f"Your label {label!r} matches an already-used theme. "
                "If THIS cluster is truly a different theme, name that "
                "different English theme; if it is the same theme "
                "(including a translation), output exactly "
                f"{matched!r}.\n" + user
            )
            if _labels_conflict(retry, matched) or any(
                _labels_conflict(retry, u) for u in used_labels
            ):
                # Prefer the canonical existing English label
                hit = next(
                    u
                    for u in used_labels
                    if _labels_conflict(retry, u) or _labels_conflict(label, u)
                )
                tqdm.write(
                    f"  cluster {c}: same theme as {hit!r} "
                    f"(likely translation split) → merging"
                )
                label = hit
            else:
                label = retry

        if _is_vague_label(label):
            label = "Mixed / Unclear"

        proposed[c] = label
        if label not in used_labels:
            used_labels.append(label)
        tqdm.write(f"  cluster {c}: {label}")

    assignments, proposed, noise_cluster_id = collapse_same_label_clusters(
        assignments, proposed, noise_cluster_id=noise_cluster_id
    )
    return assignments, proposed, noise_cluster_id
