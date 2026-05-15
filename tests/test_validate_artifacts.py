import json
import subprocess
import sys
from pathlib import Path

import yaml

from ops.validate_artifacts import main
from ops.validators.frontmatter import FrontmatterValidator
from ops.validators.references import ReferencesValidator


def write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def copy_schema(source: str, repo_root: Path) -> None:
    write_text(
        repo_root / "schemas" / source,
        Path("schemas", source).read_text(encoding="utf-8"),
    )


def valid_references() -> dict:
    return {
        "git": [
            {
                "name": "billing-service",
                "url": "git@github.com:org/billing-service.git",
                "branch": "main",
            }
        ],
        "spreadsheets": [
            {
                "name": "legacy-requirements",
                "type": "file",
                "path": "sources/spreadsheets/legacy-requirements.xlsx",
            },
            {
                "name": "product-requirements",
                "type": "google",
                "url": "https://docs.google.com/spreadsheets/d/example/edit",
                "export": "xlsx",
            },
        ],
        "rfp": [{"name": "main-rfp", "path": "sources/rfp/main-rfp.pdf"}],
        "jira": {
            "instance": "https://company.atlassian.net",
            "projects": ["PLATFORM"],
        },
    }


def valid_frontmatter(inputs=None):
    return {
        "artifact_type": "system-summary",
        "generated_by": "test",
        "generated_at": "2026-05-14T12:00:00Z",
        "inputs": inputs or [],
        "input_hashes": {},
        "confidence": "high",
    }


def write_artifact(path: Path, frontmatter: dict, body: str = "# Artifact\n") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "---\n" + yaml.safe_dump(frontmatter, sort_keys=False) + "---\n" + body,
        encoding="utf-8",
    )


def make_repo(tmp_path: Path) -> Path:
    for directory in (
        "schemas",
        "normalized/requirements",
        "domain/systems",
        "domain/subdomains",
        "requirements/mapped",
        "output",
    ):
        (tmp_path / directory).mkdir(parents=True, exist_ok=True)
    copy_schema("references.schema.json", tmp_path)
    copy_schema("frontmatter.schema.json", tmp_path)
    write_text(tmp_path / "references.yaml", yaml.safe_dump(valid_references()))
    return tmp_path


def test_references_validator_accepts_valid_fixture(tmp_path):
    repo_root = make_repo(tmp_path)

    assert ReferencesValidator().run(repo_root) == []


def test_references_validator_rejects_missing_required_url(tmp_path):
    repo_root = make_repo(tmp_path)
    data = valid_references()
    del data["git"][0]["url"]
    write_text(repo_root / "references.yaml", yaml.safe_dump(data))

    errors = ReferencesValidator().run(repo_root)

    assert len(errors) == 1
    assert errors[0].path == "references.yaml"
    assert "url" in errors[0].message


def test_frontmatter_validator_accepts_valid_fixture(tmp_path):
    repo_root = make_repo(tmp_path)
    write_artifact(repo_root / "domain" / "systems" / "billing-service.md", valid_frontmatter())

    assert FrontmatterValidator(["domain/systems/*.md"]).run(repo_root) == []


def test_frontmatter_validator_rejects_invalid_fixture(tmp_path):
    repo_root = make_repo(tmp_path)
    frontmatter = valid_frontmatter()
    del frontmatter["generated_by"]
    write_artifact(repo_root / "domain" / "systems" / "billing-service.md", frontmatter)

    errors = FrontmatterValidator(["domain/systems/*.md"]).run(repo_root)

    assert len(errors) == 1
    assert errors[0].path == "domain/systems/billing-service.md"
    assert "generated_by" in errors[0].message


def test_broken_file_references_accepts_existing_inputs(tmp_path, monkeypatch):
    repo_root = make_repo(tmp_path)
    write_text(repo_root / "import" / "git" / "billing-service" / "README.md", "# repo\n")
    write_artifact(
        repo_root / "domain" / "systems" / "billing-service.md",
        valid_frontmatter(["import/git/billing-service"]),
    )
    monkeypatch.chdir(repo_root)

    assert main(["validate", "broken-file-references"]) == 0


def test_broken_file_references_rejects_missing_inputs(tmp_path, monkeypatch):
    repo_root = make_repo(tmp_path)
    write_artifact(
        repo_root / "domain" / "systems" / "billing-service.md",
        valid_frontmatter(["import/git/billing-service"]),
    )
    monkeypatch.chdir(repo_root)

    assert main(["validate", "broken-file-references"]) == 1


def test_missing_summaries_accepts_known_suggested_systems(tmp_path, monkeypatch):
    repo_root = make_repo(tmp_path)
    write_artifact(repo_root / "domain" / "systems" / "billing-service.md", valid_frontmatter())
    write_text(
        repo_root / "domain" / "suggested-boundaries.yaml",
        yaml.safe_dump({"subdomains": [{"name": "billing", "systems": ["billing-service"]}]}),
    )
    monkeypatch.chdir(repo_root)

    assert main(["validate", "missing-summaries"]) == 0


def test_missing_summaries_rejects_unknown_suggested_systems(tmp_path, monkeypatch):
    repo_root = make_repo(tmp_path)
    write_text(
        repo_root / "domain" / "suggested-boundaries.yaml",
        yaml.safe_dump({"subdomains": [{"name": "billing", "systems": ["billing-service"]}]}),
    )
    monkeypatch.chdir(repo_root)

    assert main(["validate", "missing-summaries"]) == 1


def test_unknown_system_names_accepts_known_requirements_systems(tmp_path, monkeypatch):
    repo_root = make_repo(tmp_path)
    write_artifact(repo_root / "domain" / "systems" / "billing-service.md", valid_frontmatter())
    write_text(
        repo_root / "requirements" / "mapped" / "requirements-mapping.yaml",
        yaml.safe_dump({"mappings": [{"id": "REQ-1", "affected_systems": ["billing-service"]}]}),
    )
    monkeypatch.chdir(repo_root)

    assert main(["validate", "unknown-system-names"]) == 0


def test_unknown_system_names_rejects_unresolved_requirements_systems(tmp_path, monkeypatch):
    repo_root = make_repo(tmp_path)
    write_text(
        repo_root / "requirements" / "mapped" / "requirements-mapping.yaml",
        yaml.safe_dump({"mappings": [{"id": "REQ-1", "affected_systems": ["billing-service"]}]}),
    )
    monkeypatch.chdir(repo_root)

    assert main(["validate", "unknown-system-names"]) == 1


def test_validate_all_skips_missing_optional_artifacts(tmp_path, monkeypatch):
    repo_root = make_repo(tmp_path)
    monkeypatch.chdir(repo_root)

    assert main(["validate", "all"]) == 0


def test_json_output_shape_for_failures(tmp_path, monkeypatch, capsys):
    repo_root = make_repo(tmp_path)
    data = valid_references()
    del data["git"][0]["url"]
    write_text(repo_root / "references.yaml", yaml.safe_dump(data))
    monkeypatch.chdir(repo_root)

    assert main(["--json", "validate", "references"]) == 1
    payload = json.loads(capsys.readouterr().out)

    assert payload["errors"][0]["validator"] == "references"
    assert payload["errors"][0]["path"] == "references.yaml"
    assert "url" in payload["errors"][0]["message"]


def test_help_lists_registered_validators():
    result = subprocess.run(
        [sys.executable, "-m", "ops.validate_artifacts", "--help"],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "registered validators:" in result.stdout
    assert "references" in result.stdout
    assert "frontmatter" in result.stdout
    assert "broken-file-references" in result.stdout


def test_seed_references_validate_with_cli():
    result = subprocess.run(
        [sys.executable, "-m", "ops.validate_artifacts", "validate", "references"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "validation passed: references" in result.stdout
