"""Tests for CLI verbosity / logging helpers."""

from __future__ import annotations

import logging

from rse_survey.logging_config import (
    configure_logging,
    current_mode,
    flow_result,
    get_logger,
    is_debug,
)


def test_configure_logging_modes():
    configure_logging("silent")
    assert current_mode() == "silent"
    assert not is_debug()
    assert get_logger().level == logging.WARNING
    assert flow_result({"ok": True}) is None

    configure_logging("verbose")
    assert current_mode() == "verbose"
    assert not is_debug()
    assert get_logger().level == logging.INFO
    assert flow_result({"ok": True}) is None

    configure_logging("debug")
    assert current_mode() == "debug"
    assert is_debug()
    assert get_logger().level == logging.DEBUG
    assert flow_result({"ok": True}) == {"ok": True}
