"""Validation for references.yaml."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from jsonschema.exceptions import ValidationError as JsonSchemaValidationError

from ops.validators import ValidationError, register_validator


@dataclass
class ReferencesValidator:
    name: str = "references"

    def run(self, repo_root: Path) -> list[ValidationError]:
        path = repo_root / "references.yaml"
        schema_path = repo_root / "schemas" / "references.schema.json"
        errors: list[ValidationError] = []

        try:
            data = _read_yaml(path)
        except FileNotFoundError:
            return [ValidationError(self.name, "references.yaml", "file does not exist")]
        except yaml.YAMLError as exc:
            return [ValidationError(self.name, "references.yaml", f"invalid YAML: {exc}")]

        try:
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
        except FileNotFoundError:
            return [
                ValidationError(
                    self.name,
                    "schemas/references.schema.json",
                    "schema file does not exist",
                )
            ]

        validator = Draft202012Validator(schema)
        for error in sorted(validator.iter_errors(data), key=_schema_error_sort_key):
            errors.append(
                ValidationError(
                    self.name,
                    "references.yaml",
                    _format_schema_error(error),
                )
            )
        return errors


def _read_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _schema_error_sort_key(error: JsonSchemaValidationError) -> tuple[str, str]:
    return (".".join(str(part) for part in error.path), error.message)


def _format_schema_error(error: JsonSchemaValidationError) -> str:
    location = "$"
    if error.path:
        location = "$." + ".".join(str(part) for part in error.path)
    return f"{location}: {error.message}"


register_validator(
    "references",
    ReferencesValidator,
    "validate references.yaml against schemas/references.schema.json",
)
