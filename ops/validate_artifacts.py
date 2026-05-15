"""Command-line artifact validation entry point."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from ops.validators import ValidationError, load_validators, make_validator


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    repo_root = Path.cwd()

    if args.command != "validate":
        raise AssertionError(f"Unhandled command: {args.command}")

    errors = _run_validate(args.target, args.paths, repo_root)
    if args.json:
        _print_json(errors)
    else:
        _print_human(args.target, errors)
    return 1 if errors else 0


def _run_validate(target: str, paths: list[str], repo_root: Path) -> list[ValidationError]:
    if target == "all":
        errors: list[ValidationError] = []
        for name in load_validators():
            validator = make_validator(name)
            errors.extend(validator.run(repo_root))
        return sorted(errors, key=_error_sort_key)

    kwargs = {}
    if target == "frontmatter":
        kwargs["patterns"] = paths
    elif paths:
        raise SystemExit(f"validator '{target}' does not accept path arguments")

    validator = make_validator(target, **kwargs)
    return sorted(validator.run(repo_root), key=_error_sort_key)


def _build_parser() -> argparse.ArgumentParser:
    validators = load_validators()
    validator_lines = ["registered validators:"]
    for name, spec in validators.items():
        validator_lines.append(f"  {name:<24} {spec.description}")

    parser = argparse.ArgumentParser(
        prog="python -m ops.validate_artifacts",
        description="Validate structured project intelligence artifacts.",
        epilog="\n".join(validator_lines),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON output",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser(
        "validate",
        help="run a registered validator or all validators",
    )
    validate_parser.add_argument(
        "target",
        choices=["all", *validators.keys()],
        help="validator to run",
    )
    validate_parser.add_argument(
        "paths",
        nargs="*",
        help="path or glob arguments for validators that accept them",
    )
    return parser


def _print_json(errors: list[ValidationError]) -> None:
    payload = {
        "errors": [
            {
                "validator": error.validator,
                "path": error.path,
                "message": error.message,
            }
            for error in errors
        ]
    }
    print(json.dumps(payload, indent=2, sort_keys=True))


def _print_human(target: str, errors: list[ValidationError]) -> None:
    if not errors:
        print(f"validation passed: {target}")
        return

    print(f"validation failed: {target}", file=sys.stderr)
    grouped: dict[str, list[ValidationError]] = defaultdict(list)
    for error in errors:
        grouped[error.path].append(error)

    for path in sorted(grouped):
        print(path, file=sys.stderr)
        for error in grouped[path]:
            print(f"  [{error.validator}] {error.message}", file=sys.stderr)


def _error_sort_key(error: ValidationError) -> tuple[str, str, str]:
    return (error.path, error.validator, error.message)


if __name__ == "__main__":
    raise SystemExit(main())
