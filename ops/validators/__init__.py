"""Pluggable artifact validator registry."""

from __future__ import annotations

import importlib
import pkgutil
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Protocol


@dataclass(frozen=True)
class ValidationError:
    """A single validation failure suitable for human or JSON output."""

    validator: str
    path: str
    message: str


class Validator(Protocol):
    """Uniform interface implemented by every artifact validator."""

    name: str

    def run(self, repo_root: Path) -> list[ValidationError]:
        """Return validation failures for this repository."""


@dataclass(frozen=True)
class ValidatorSpec:
    name: str
    factory: Callable[..., Validator]
    description: str


_REGISTRY: dict[str, ValidatorSpec] = {}
_LOADED = False


def register_validator(
    name: str,
    factory: Callable[..., Validator],
    description: str,
) -> None:
    """Register a validator factory.

    Validator modules call this at import time. Later work packages can add a
    module under ops/validators/ and a schema under schemas/ without changing
    ops.validate_artifacts.
    """

    if name in _REGISTRY:
        raise ValueError(f"Duplicate validator registered: {name}")
    _REGISTRY[name] = ValidatorSpec(name=name, factory=factory, description=description)


def load_validators() -> dict[str, ValidatorSpec]:
    """Import validator modules and return the registry."""

    global _LOADED
    if not _LOADED:
        package_name = __name__
        for module_info in pkgutil.iter_modules(__path__):
            if module_info.name.startswith("_"):
                continue
            importlib.import_module(f"{package_name}.{module_info.name}")
        _LOADED = True
    return dict(sorted(_REGISTRY.items()))


def make_validator(name: str, **kwargs: object) -> Validator:
    """Build a registered validator by name."""

    validators = load_validators()
    try:
        spec = validators[name]
    except KeyError as exc:
        known = ", ".join(validators)
        raise KeyError(f"Unknown validator '{name}'. Registered validators: {known}") from exc
    return spec.factory(**kwargs)


def repo_relative(repo_root: Path, path: Path) -> str:
    """Return a stable repository-relative path for output."""

    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()
