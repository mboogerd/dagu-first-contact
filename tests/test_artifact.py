import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import validate
from jsonschema.exceptions import ValidationError

from ops._artifact import (
    enforce_required_keys,
    hash_path,
    now_iso,
    read_frontmatter,
    write_artifact,
)


SCHEMA = json.loads(Path("schemas/frontmatter.schema.json").read_text(encoding="utf-8"))


def valid_frontmatter():
    return {
        "artifact_type": "system-summary",
        "generated_by": "20-domain-analysis",
        "generated_at": "2026-05-14T12:00:00Z",
        "inputs": ["import/git/billing-service"],
        "input_hashes": {"import/git/billing-service": "abc123"},
        "confidence": "medium",
        "extra": {"allowed": True},
    }


def test_round_trip_read_write(tmp_path):
    path = tmp_path / "artifact.md"
    body = "# Billing Service\n\nSummary text.\n"

    write_artifact(path, valid_frontmatter(), body)

    frontmatter, parsed_body = read_frontmatter(path)
    assert frontmatter == valid_frontmatter()
    assert parsed_body == body


def test_read_without_frontmatter_returns_empty_metadata(tmp_path):
    path = tmp_path / "plain.md"
    path.write_text("# Plain\n", encoding="utf-8")

    assert read_frontmatter(path) == ({}, "# Plain\n")


def test_atomic_write_keeps_original_when_replace_fails(tmp_path, monkeypatch):
    path = tmp_path / "artifact.md"
    path.write_text("original\n", encoding="utf-8")

    def fail_replace(src, dst):
        raise RuntimeError("simulated replace failure")

    monkeypatch.setattr(os, "replace", fail_replace)

    with pytest.raises(RuntimeError, match="simulated replace failure"):
        write_artifact(path, valid_frontmatter(), "new\n")

    assert path.read_text(encoding="utf-8") == "original\n"
    assert not (tmp_path / "artifact.md.tmp").exists()


def test_directory_hashing_is_stable_and_content_sensitive(tmp_path):
    left = tmp_path / "left"
    right = tmp_path / "right"
    for root in (left, right):
        (root / "nested").mkdir(parents=True)
        (root / "nested" / "b.txt").write_text("b\n", encoding="utf-8")
        (root / "a.txt").write_text("a\n", encoding="utf-8")
        (root / ".DS_Store").write_text("ignored\n", encoding="utf-8")
        (root / "__pycache__").mkdir()
        (root / "__pycache__" / "ignored.pyc").write_bytes(b"ignored")

    assert hash_path(left) == hash_path(right)

    (right / "a.txt").write_text("changed\n", encoding="utf-8")
    assert hash_path(left) != hash_path(right)


def test_schema_accepts_valid_frontmatter():
    validate(valid_frontmatter(), SCHEMA)


def test_schema_rejects_missing_artifact_type():
    frontmatter = valid_frontmatter()
    del frontmatter["artifact_type"]

    with pytest.raises(ValidationError):
        validate(frontmatter, SCHEMA)


def test_required_key_enforcement():
    enforce_required_keys({"artifact_type": "system-summary"}, ["artifact_type"])

    with pytest.raises(ValueError, match="generated_by"):
        enforce_required_keys({"artifact_type": "system-summary"}, ["artifact_type", "generated_by"])


def test_now_iso_returns_utc_rfc3339():
    assert re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", now_iso())


def test_import_proof_matches_acceptance_command_shape():
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from ops._artifact import write_artifact, read_frontmatter, hash_path, now_iso; print('ok')",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == "ok"
