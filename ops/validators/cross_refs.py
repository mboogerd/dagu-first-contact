"""Cross-artifact validation checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import yaml

from ops._artifact import read_frontmatter
from ops.validators import ValidationError, register_validator, repo_relative
from ops.validators.frontmatter import DEFAULT_ARTIFACT_ROOTS


@dataclass
class BrokenFileReferencesValidator:
    name: str = "broken-file-references"

    def run(self, repo_root: Path) -> list[ValidationError]:
        errors: list[ValidationError] = []
        for path in _iter_markdown_artifacts(repo_root):
            relpath = repo_relative(repo_root, path)
            try:
                frontmatter, _body = read_frontmatter(path)
            except ValueError as exc:
                errors.append(ValidationError(self.name, relpath, str(exc)))
                continue
            if not frontmatter:
                continue

            references = []
            for key in ("inputs", "sources"):
                references.extend(_string_values(frontmatter.get(key)))

            for reference in references:
                if _is_external_reference(reference):
                    continue
                target = _path_without_fragment(reference)
                if not target:
                    continue
                if not (repo_root / target).exists():
                    errors.append(
                        ValidationError(
                            self.name,
                            relpath,
                            f"referenced path does not exist: {reference}",
                        )
                    )
        return errors


@dataclass
class MissingSummariesValidator:
    name: str = "missing-summaries"

    def run(self, repo_root: Path) -> list[ValidationError]:
        boundaries_path = repo_root / "domain" / "suggested-boundaries.yaml"
        if not boundaries_path.exists():
            return []

        try:
            data = _read_yaml(boundaries_path)
        except yaml.YAMLError as exc:
            return [
                ValidationError(
                    self.name,
                    "domain/suggested-boundaries.yaml",
                    f"invalid YAML: {exc}",
                )
            ]

        known_systems = _known_system_names(repo_root)
        errors = []
        for system_name in sorted(_systems_from_boundaries(data)):
            if system_name not in known_systems:
                errors.append(
                    ValidationError(
                        self.name,
                        "domain/suggested-boundaries.yaml",
                        f"missing domain/systems/{system_name}.md for suggested system '{system_name}'",
                    )
                )
        return errors


@dataclass
class UnknownSystemNamesValidator:
    name: str = "unknown-system-names"

    def run(self, repo_root: Path) -> list[ValidationError]:
        known_systems = _known_system_names(repo_root)
        if not (repo_root / "requirements").exists():
            return []

        errors: list[ValidationError] = []
        for path in _iter_requirement_artifacts(repo_root):
            relpath = repo_relative(repo_root, path)
            try:
                data = _load_requirement_artifact(path)
            except ValueError as exc:
                errors.append(ValidationError(self.name, relpath, str(exc)))
                continue
            except yaml.YAMLError as exc:
                errors.append(ValidationError(self.name, relpath, f"invalid YAML: {exc}"))
                continue

            for system_name in sorted(_values_for_key(data, "affected_systems")):
                if system_name not in known_systems:
                    errors.append(
                        ValidationError(
                            self.name,
                            relpath,
                            f"unknown affected_systems value: {system_name}",
                        )
                    )
        return errors


def _iter_markdown_artifacts(repo_root: Path) -> list[Path]:
    paths: list[Path] = []
    for root in DEFAULT_ARTIFACT_ROOTS:
        artifact_root = repo_root / root
        if artifact_root.exists():
            paths.extend(artifact_root.rglob("*.md"))
    return sorted(path for path in paths if path.is_file())


def _iter_requirement_artifacts(repo_root: Path) -> list[Path]:
    requirements_root = repo_root / "requirements"
    candidates = []
    for suffix in ("*.yaml", "*.yml", "*.md"):
        candidates.extend(requirements_root.rglob(suffix))
    return sorted(path for path in candidates if path.is_file())


def _load_requirement_artifact(path: Path) -> Any:
    if path.suffix == ".md":
        frontmatter, _body = read_frontmatter(path)
        return frontmatter
    return _read_yaml(path)


def _read_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle)


def _known_system_names(repo_root: Path) -> set[str]:
    systems_root = repo_root / "domain" / "systems"
    if not systems_root.exists():
        return set()
    return {path.stem for path in systems_root.glob("*.md")}


def _systems_from_boundaries(data: Any) -> set[str]:
    systems = set(_values_for_key(data, "systems"))
    systems.update(_values_for_key(data, "system"))
    return systems


def _values_for_key(data: Any, key: str) -> set[str]:
    values: set[str] = set()
    if isinstance(data, dict):
        for item_key, item_value in data.items():
            if item_key == key:
                values.update(_string_values(item_value))
            else:
                values.update(_values_for_key(item_value, key))
    elif isinstance(data, list):
        for item in data:
            values.update(_values_for_key(item, key))
    return values


def _string_values(value: Any) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        values: list[str] = []
        for item in value:
            values.extend(_string_values(item))
        return values
    if isinstance(value, dict):
        values = []
        for item in value.values():
            values.extend(_string_values(item))
        return values
    return []


def _is_external_reference(reference: str) -> bool:
    return "://" in reference or reference.startswith("git@")


def _path_without_fragment(reference: str) -> str:
    return reference.split("#", 1)[0].strip()


register_validator(
    "broken-file-references",
    BrokenFileReferencesValidator,
    "check frontmatter inputs/sources paths exist on disk",
)
register_validator(
    "missing-summaries",
    MissingSummariesValidator,
    "check suggested boundaries have matching domain/systems/*.md files",
)
register_validator(
    "unknown-system-names",
    UnknownSystemNamesValidator,
    "check affected_systems values resolve to known domain systems",
)
