"""Free-text coding layer: open answers → analysis categories.

Stage 3 of the pipeline, run offline via ``rse-survey propose`` / ``apply``.
The stages read in file order:

``tokenize`` → ``seed_themes`` → ``embed`` → ``cluster`` →
``cluster_diagnostics`` → ``label`` → ``token_labels``

``workflows`` wires them into the two commands. ``token_labels.csv`` is the
handoff to analysis — nothing downstream imports the clustering internals.
"""

from rse_survey.coding.label import (
    apply_labels,
    labels_from_config,
    propose_labels,
    require_labels,
    save_labels_to_coding_yml,
)
from rse_survey.coding.models import configure_hf_cache
from rse_survey.coding.token_labels import (
    active_token_labels,
    read_token_labels_csv,
    token_labels_path,
    write_token_labels_csv,
)
from rse_survey.coding.tokenize import (
    filter_excluded_tokens,
    load_tokens,
    tokenize_series,
)
from rse_survey.coding.workflows import (
    run_apply_labels_only,
    run_propose_labels,
    run_sample_tokens,
)

__all__ = [
    "active_token_labels",
    "apply_labels",
    "configure_hf_cache",
    "filter_excluded_tokens",
    "labels_from_config",
    "load_tokens",
    "propose_labels",
    "read_token_labels_csv",
    "require_labels",
    "save_labels_to_coding_yml",
    "run_apply_labels_only",
    "run_propose_labels",
    "run_sample_tokens",
    "token_labels_path",
    "tokenize_series",
    "write_token_labels_csv",
]
