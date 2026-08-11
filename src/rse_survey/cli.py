"""CLI entrypoint for rse-survey.

Argument parsing only: every subcommand delegates to one flow in
:mod:`rse_survey.flows`. Imports are deferred into each branch so ``--help``
and cheap commands do not pay for pandas/Prefect.
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any


def _verbosity_parent() -> argparse.ArgumentParser:
    parent = argparse.ArgumentParser(add_help=False)
    group = parent.add_mutually_exclusive_group()
    group.add_argument(
        "--silent",
        action="store_const",
        const="silent",
        dest="log_mode",
        help="Warnings/errors only",
    )
    group.add_argument(
        "--verbose",
        action="store_const",
        const="verbose",
        dest="log_mode",
        help="Progress messages (default)",
    )
    group.add_argument(
        "--debug",
        action="store_const",
        const="debug",
        dest="log_mode",
        help="Debug logs and print flow return payloads",
    )
    return parent


def _print_flow_result(out: dict[str, Any] | None) -> None:
    """Print Prefect flow return payload only in debug mode."""
    from rse_survey.logging_config import is_debug

    if is_debug() and out is not None:
        print(json.dumps(out, indent=2, default=str))


def _build_parser() -> argparse.ArgumentParser:
    verbosity = _verbosity_parent()
    parser = argparse.ArgumentParser(
        prog="rse-survey",
        description="International RSE Survey analysis (Prefect + artifacts)",
        parents=[verbosity],
    )
    parser.set_defaults(log_mode="verbose")
    sub = parser.add_subparsers(dest="command", required=True)

    def add_config(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--config",
            default="config/book.yml",
            help="Path to book.yml (default: config/book.yml)",
        )

    def add_coding_config(p: argparse.ArgumentParser) -> None:
        p.add_argument(
            "--coding-config",
            default="config/free_text_coding.yml",
            help="Path to free_text_coding.yml",
        )

    validate_p = sub.add_parser(
        "validate",
        parents=[verbosity],
        help="Validate survey inputs and book.yml",
    )
    add_config(validate_p)

    sub.add_parser(
        "list-tasks",
        parents=[verbosity],
        help="List registered analysis tasks",
    )

    process = sub.add_parser(
        "process-data",
        parents=[verbosity],
        help="Process raw survey CSV into clean long-format dataset",
    )
    add_config(process)
    add_coding_config(process)

    build = sub.add_parser(
        "build-artifacts",
        parents=[verbosity],
        help="Build Quarto artifacts",
    )
    add_config(build)
    build.add_argument(
        "--question",
        action="append",
        dest="questions",
        help="Limit to question id (repeatable)",
    )

    select = sub.add_parser(
        "select-questions",
        parents=[verbosity],
        help=(
            "Select-question table + bar plot "
            "(grouping: focus | by_age | between_countries)"
        ),
    )
    add_config(select)
    select.add_argument("--question", required=True)
    select.add_argument(
        "--grouping",
        default="focus",
        choices=["focus", "by_age", "between_countries"],
        help="Grouping variable (default: focus)",
    )

    sync = sub.add_parser(
        "sync-quarto",
        parents=[verbosity],
        help="Write thin Quarto chapters + recoding appendix from book.yml",
    )
    add_config(sync)

    propose = sub.add_parser(
        "propose",
        parents=[verbosity],
        help="HF free-text: cluster + draft labels into free_text_coding.yml",
    )
    add_config(propose)
    add_coding_config(propose)
    propose.add_argument("--question", required=True)
    propose.add_argument(
        "--overwrite-labels",
        action="store_true",
        help="Replace existing labels for this question",
    )
    propose.add_argument(
        "--sample-tokens",
        type=int,
        default=None,
        metavar="N",
        help="Also print N tokens per cluster after proposing",
    )

    apply_p = sub.add_parser(
        "apply",
        parents=[verbosity],
        help=(
            "HF free-text: apply YAML cluster labels → token_labels.csv "
            "(or --from-csv after manual token edits)"
        ),
    )
    add_coding_config(apply_p)
    apply_p.add_argument("--question", required=True)
    apply_p.add_argument(
        "--from-csv",
        action="store_true",
        help=(
            "Keep token_labels.csv as edited; only refresh category_summary "
            "(after reallocating individual tokens)"
        ),
    )
    apply_p.add_argument(
        "--sample-tokens",
        type=int,
        default=None,
        metavar="N",
        help="Also print N tokens per cluster after applying",
    )

    sample = sub.add_parser(
        "sample-tokens",
        parents=[verbosity],
        help="Print tokens per category using labels from token_labels.csv",
    )
    add_coding_config(sample)
    sample.add_argument("--question", required=True)
    sample.add_argument(
        "-n",
        "--sample-tokens",
        type=int,
        default=10,
        dest="sample_tokens",
        metavar="N",
        help="Tokens per category (default: 10)",
    )
    return parser


def _cmd_list_tasks() -> None:
    from rse_survey.analysis.registry import ensure_builtin_tasks_loaded, list_tasks

    ensure_builtin_tasks_loaded()
    for name in list_tasks():
        print(name)


def _cmd_validate(args: argparse.Namespace) -> None:
    from rse_survey.config.book_config import load_book_config
    from rse_survey.data.validation import InputValidationError, validate_inputs

    try:
        book = load_book_config(args.config)
        result = validate_inputs(book, raise_on_error=True)
    except InputValidationError as exc:
        print("VALIDATION FAILED", file=sys.stderr)
        for issue in exc.result.issues:
            print(f"  [{issue.level}] {issue.code}: {issue.message}", file=sys.stderr)
        sys.exit(1)
    print("OK")
    for w in result.warnings:
        print(f"  [warning] {w.code}: {w.message}")


def main(argv: list[str] | None = None) -> None:
    args = _build_parser().parse_args(argv)

    from rse_survey.logging_config import configure_logging

    configure_logging(args.log_mode)

    if args.command == "list-tasks":
        _cmd_list_tasks()
        return

    if args.command == "validate":
        _cmd_validate(args)
        return

    if args.command == "process-data":
        from rse_survey.flows.process_data import process_data_flow

        _print_flow_result(
            process_data_flow(
                book_config=args.config,
                coding_config=args.coding_config,
            )
        )
        return

    if args.command == "build-artifacts":
        from rse_survey.flows.build_artifacts import build_artifacts_flow

        _print_flow_result(
            build_artifacts_flow(
                book_config=args.config,
                question_ids=args.questions,
            )
        )
        return

    if args.command == "select-questions":
        from rse_survey.flows.select_questions import select_questions_flow

        _print_flow_result(
            select_questions_flow(
                args.question,
                grouping_variable=args.grouping,
                book_config=args.config,
            )
        )
        return

    if args.command == "sync-quarto":
        from rse_survey.flows.sync_book import sync_book_flow

        _print_flow_result(sync_book_flow(book_config=args.config))
        return

    if args.command == "propose":
        from rse_survey.flows.code_free_text import propose_flow

        _print_flow_result(
            propose_flow(
                args.question,
                book_config=args.config,
                coding_config=args.coding_config,
                overwrite_labels=args.overwrite_labels,
                sample_tokens=args.sample_tokens,
            )
        )
        return

    if args.command == "apply":
        from rse_survey.flows.code_free_text import apply_flow

        _print_flow_result(
            apply_flow(
                args.question,
                coding_config=args.coding_config,
                sample_tokens=args.sample_tokens,
                from_csv=args.from_csv,
            )
        )
        return

    if args.command == "sample-tokens":
        from rse_survey.coding.workflows import run_sample_tokens
        from rse_survey.config.coding_config import load_question_coding

        cfg, _path = load_question_coding(args.question, coding_path=args.coding_config)
        run_sample_tokens(cfg, args.sample_tokens)
        return

    _build_parser().error(f"Unknown command {args.command}")


if __name__ == "__main__":
    main()
