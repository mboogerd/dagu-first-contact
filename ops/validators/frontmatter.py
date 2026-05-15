"""Validation for generated artifact frontmatter."""

from __future__ import annotations

import glob
import json
from dataclasses import dataclass, field
from pathlib import Path

from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

from ops._artifact import read_frontmatter
from ops.validators import ValidationError, register_validator, repo_relative


DEFAULT_ARTIFACT_ROOTS = ("normalized", "domain", "requirements", "output")


@dataclass
class FrontmatterValidator:
    patterns: list[str] = field(default_factory=list)
    name: str = "frontmatter"

    def run(self, repo_root: Path) -> list[ValidationError]:
        schema_path = repo_root / "schemas" / "frontmatter.schema.json"
        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return [
                ValidationError(
                    self.name,
                    "schemas/frontmatter.schema.json",
                    "schema file does not exist",
                )
            ]

        validator = Draft202012Validator(schema)
        errors: list[ValidationError] = []
        paths = _resolve_patterns(repo_root, self.patterns)

        for path in paths:
            relpath = repo_relative(repo_root, path)
            try:
                frontmatter, _body = read_frontmatter(path)
            except ValueError as exc:
                errors.append(ValidationError(self.name, relpath, str(exc)))
                continue
            except FileNotFoundError:
                errors.append(ValidationError(self.name, relpath, "file does not exist"))
                continue

            if not frontmatter:
                errors.append(ValidationError(self.name, relpath, "missing YAML frontmatter"))
                continue

            for error in sorted(validator.iter_errors(frontmatter), key=_schema_error_sort_key):
                errors.append(ValidationError(self.name, relpath, _format_schema_error(error)))

        return errors


def _resolve_patterns(repo_root: Path, patterns: list[str]) -> list[Path]:
    if not patterns:
        paths: list[Path] = []
        for root in DEFAULT_ARTIFACT_ROOTS:
            artifact_root = repo_root / root
            if artifact_root.exists():
                paths.extend(artifact_root.rglob("*.md"))
        return sorted(path for path in paths if path.is_file())

    paths = []
    for pattern in patterns:
        absolute_pattern = str((repo_root / pattern).resolve())
        matches = [Path(match) for match in glob.glob(absolute_pattern, recursive=True)]
        if matches:
            paths.extend(path for path in matches if path.is_file())
        else:
            paths.append(repo_root / pattern)
    return sorted(set(paths))


def _schema_error_sort_key(error: JsonSchemaValidationError) -> tuple[str, str]:
    return (".".join(str(part) for part in error.path), error.message)


def _format_schema_error(error: JsonSchemaValidationError) -> str:
    location = "$"
    if error.path:
        location = "$." + ".".join(str(part) for part in error.path)
    return f"{location}: {error.message}"


register_validator(
    "frontmatter",
    FrontmatterValidator,
    "validate markdown artifact frontmatter against schemas/frontmatter.schema.json",
)
