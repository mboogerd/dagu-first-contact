"""Helpers for generated artifact frontmatter and content hashing."""

from __future__ import annotations

import hashlib
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import yaml


IGNORED_TREE_NAMES = {".DS_Store", "__pycache__"}

__all__ = [
    "enforce_required_keys",
    "hash_path",
    "now_iso",
    "read_frontmatter",
    "write_artifact",
]


def now_iso() -> str:
    """Return the current UTC time as RFC 3339 with a trailing Z."""

    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def read_frontmatter(path: str | Path) -> tuple[dict[str, Any], str]:
    """Read YAML frontmatter from a markdown-style artifact.

    Returns an empty dict and the full file content when no frontmatter fence is
    present. Raises ValueError when a frontmatter opening fence has no close.
    """

    content = Path(path).read_text(encoding="utf-8")
    lines = content.splitlines(keepends=True)

    if not lines or lines[0].strip() != "---":
        return {}, content

    closing_index = None
    for index, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            closing_index = index
            break

    if closing_index is None:
        raise ValueError(f"Missing closing frontmatter fence: {path}")

    raw_frontmatter = "".join(lines[1:closing_index])
    parsed = yaml.safe_load(raw_frontmatter) if raw_frontmatter.strip() else {}
    if parsed is None:
        parsed = {}
    if not isinstance(parsed, dict):
        raise ValueError(f"Frontmatter must be a mapping: {path}")

    body = "".join(lines[closing_index + 1 :])
    return parsed, body


def write_artifact(path: str | Path, frontmatter: dict[str, Any], body: str) -> None:
    """Atomically write an artifact with YAML frontmatter and body text."""

    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = target.with_name(f"{target.name}.tmp")

    yaml_text = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True)
    content = f"---\n{yaml_text}---\n{body}"

    try:
        tmp_path.write_text(content, encoding="utf-8")
        os.replace(tmp_path, target)
    except Exception:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass
        raise


def hash_path(path: str | Path) -> str:
    """Hash a file or a directory tree using stable sha256 semantics."""

    target = Path(path)
    if target.is_file():
        return _hash_file(target)
    if target.is_dir():
        return _hash_directory(target)
    raise FileNotFoundError(path)


def enforce_required_keys(frontmatter: dict[str, Any], required: Iterable[str]) -> None:
    """Raise ValueError when required frontmatter keys are missing."""

    missing = [key for key in required if key not in frontmatter]
    if missing:
        joined = ", ".join(missing)
        raise ValueError(f"Missing required frontmatter keys: {joined}")


def _hash_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _hash_directory(path: Path) -> str:
    digest = hashlib.sha256()
    for file_path in _iter_hashable_files(path):
        relpath = file_path.relative_to(path).as_posix()
        digest.update(relpath.encode("utf-8"))
        digest.update(b"\0")
        digest.update(_hash_file(file_path).encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()


def _iter_hashable_files(path: Path) -> list[Path]:
    files: list[Path] = []
    for root, dirnames, filenames in os.walk(path):
        dirnames[:] = sorted(name for name in dirnames if name not in IGNORED_TREE_NAMES)
        for filename in sorted(filenames):
            if filename in IGNORED_TREE_NAMES:
                continue
            files.append(Path(root) / filename)
    return sorted(files, key=lambda item: item.relative_to(path).as_posix())
