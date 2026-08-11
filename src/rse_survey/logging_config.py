"""CLI verbosity modes mapped onto standard logging levels.

Modes (CLI-facing):
  silent  → WARNING  (errors/warnings only)
  verbose → INFO     (progress; default)
  debug   → DEBUG    (internals + flow return payloads)
"""

from __future__ import annotations

import logging
import os
from typing import Any, Literal

Verbosity = Literal["silent", "verbose", "debug"]

_LEVEL_BY_MODE: dict[Verbosity, int] = {
    "silent": logging.WARNING,
    "verbose": logging.INFO,
    "debug": logging.DEBUG,
}

_PREFECT_LEVEL_NAME: dict[Verbosity, str] = {
    "silent": "ERROR",
    "verbose": "WARNING",
    "debug": "INFO",
}

_PREFECT_LEVEL: dict[Verbosity, int] = {
    "silent": logging.ERROR,
    "verbose": logging.WARNING,
    "debug": logging.INFO,
}

_mode: Verbosity = "verbose"

LOGGER_NAME = "rse_survey"


def configure_logging(mode: Verbosity = "verbose") -> None:
    """Configure the package logger for a CLI verbosity mode."""
    global _mode
    _mode = mode
    level = _LEVEL_BY_MODE[mode]

    # Prefetch Prefect's level before flows import / start a server
    os.environ["PREFECT_LOGGING_LEVEL"] = _PREFECT_LEVEL_NAME[mode]

    log = logging.getLogger(LOGGER_NAME)
    log.handlers.clear()
    handler = logging.StreamHandler()
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter("%(levelname)s %(name)s: %(message)s"))
    log.addHandler(handler)
    log.setLevel(level)
    log.propagate = False

    logging.getLogger("prefect").setLevel(_PREFECT_LEVEL[mode])
    for name in ("httpx", "httpcore", "urllib3", "asyncio", "markdown_it"):
        logging.getLogger(name).setLevel(logging.WARNING)


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a child of the package logger (or the package logger itself)."""
    if name is None or name == LOGGER_NAME:
        return logging.getLogger(LOGGER_NAME)
    if name.startswith(f"{LOGGER_NAME}."):
        return logging.getLogger(name)
    return logging.getLogger(f"{LOGGER_NAME}.{name}")


def current_mode() -> Verbosity:
    return _mode


def is_debug() -> bool:
    return _mode == "debug"


def flow_result(payload: dict[str, Any]) -> dict[str, Any] | None:
    """Return flow payload only in debug mode; otherwise ``None``.

    Call at the end of Prefect flows so callers/CLI only see diagnostics
    when ``--debug`` is set.
    """
    if is_debug():
        get_logger("flow").debug("flow result: %s", payload)
        return payload
    return None
