"""Configuration layer: YAML files under ``config/`` → typed objects.

Stage 1 of the pipeline. Depends on nothing else in the package.
"""

from rse_survey.config.book_config import (
    PRESENTATION_MODES,
    BookConfig,
    QuestionConfig,
    load_book_config,
    load_defaults,
    resolve_presentation,
)
from rse_survey.config.coding_config import (
    coding_config_path,
    load_free_text_coding,
    load_question_coding,
)
from rse_survey.config.paths import (
    CLEAN_LONG_NAME,
    CLEAN_META_NAME,
    DEFAULT_PROCESSED_DIR,
    REPO_ROOT,
    artifacts_root,
    clean_long_path,
    hf_cache_root,
    processed_dir_for,
    question_cache_dir,
    resolve_repo_path,
)

__all__ = [
    "CLEAN_LONG_NAME",
    "CLEAN_META_NAME",
    "DEFAULT_PROCESSED_DIR",
    "PRESENTATION_MODES",
    "REPO_ROOT",
    "BookConfig",
    "QuestionConfig",
    "artifacts_root",
    "clean_long_path",
    "coding_config_path",
    "hf_cache_root",
    "load_book_config",
    "load_defaults",
    "load_free_text_coding",
    "load_question_coding",
    "processed_dir_for",
    "question_cache_dir",
    "resolve_presentation",
    "resolve_repo_path",
]
