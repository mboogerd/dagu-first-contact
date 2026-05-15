# Project Intelligence Pipeline

This repository contains the local-first scaffold for a Dagu-based project intelligence pipeline. The intended flow is:

```text
raw sources
  -> imported local artifacts
  -> normalized markdown/JSON artifacts
  -> system and domain summaries
  -> requirement mappings, status, conflicts, and resolutions
  -> final consolidated report
```

The source of truth for behavior is [SPECIFICATION.md](SPECIFICATION.md). Work packages are tracked in [.plan/README.md](.plan/README.md), with WP-01 establishing this skeleton and later WPs adding deterministic scripts, Dagu workflows, validation, fixtures, and smoke tests.

## Repository Layout

- `references.yaml` declares external source systems and seed inputs.
- `dagu/` will hold Dagu workflow YAML files in later work packages.
- `ops/` will hold deterministic Python operational scripts in later work packages.
- `generated/` stores generated helper code and other derived tooling.
- `sources/` stores human-supplied source files that are referenced by `references.yaml`.
- `import/` stores local imported copies of external systems.
- `normalized/` stores normalized markdown and JSON artifacts.
- `domain/` stores system, subdomain, interaction, and domain analysis artifacts.
- `requirements/` stores extracted, mapped, classified, conflicting, and resolved requirements.
- `output/` stores final report artifacts.
- `.state/` stores local run state such as hashes and run metadata.

Runtime and source artifact directories are intentionally ignored by default, while placeholder files keep the expected folder structure visible in git.

## Setup

No executable pipeline code is part of WP-01. For now, setup is limited to preparing local configuration for later work packages:

```bash
cp .env.example .env
```

Then edit `.env` with local credentials and paths. Do not commit real secrets.

## Environment Contract

Later work packages read these variables when their related integrations are enabled:

- `DAGU_BASE_URL`: Base URL for the Dagu API used by the optional sidecar watcher.
- `DAGU_API_TOKEN`: Token for Dagu API calls.
- `JIRA_BASE_URL`: Atlassian site URL, such as `https://example.atlassian.net`.
- `JIRA_EMAIL`: Jira account email for API authentication.
- `JIRA_API_TOKEN`: Jira API token paired with `JIRA_EMAIL`.
- `GOOGLE_APPLICATION_CREDENTIALS`: Path to a Google service account credentials JSON file for Google Sheets export.

## Artifact Frontmatter

Generated artifacts use YAML frontmatter between `---` fences so later workflow steps can trace source inputs and recompute safely. Use `ops._artifact.write_artifact` to write artifacts and `ops._artifact.read_frontmatter` to read them; path values should be resolved relative to the repository root before writing.

```yaml
---
artifact_type: system-summary
generated_by: 20-domain-analysis
generated_at: 2026-05-14T12:00:00Z
inputs:
  - import/git/billing-service
input_hashes:
  import/git/billing-service: abc123
confidence: medium
---
```

`artifact_type`, `generated_by`, `generated_at`, `inputs`, and `input_hashes` are required by `schemas/frontmatter.schema.json`. `confidence` is optional for deterministic artifacts and may be `high`, `medium`, `low`, or `unknown`.

## Artifact Validation

Validate structured inputs and generated artifacts with:

```bash
python -m ops.validate_artifacts validate references
python -m ops.validate_artifacts validate all
python -m ops.validate_artifacts validate frontmatter "domain/systems/*.md"
python -m ops.validate_artifacts --json validate all
```

`validate all` runs every registered validator. Validators are discovered from `ops/validators/`; each module registers itself with `register_validator(...)`. To add a later artifact type, add its JSON Schema under `schemas/` and add a validator module under `ops/validators/` that implements `run(repo_root)`. No edits to `ops/validate_artifacts.py` are required for the new validator to appear in `--help` and participate in `validate all`.

## Verification

The WP-01 scaffold can be checked with:

```bash
test -f references.yaml && python -c "import yaml;yaml.safe_load(open('references.yaml'))"
test -f .gitignore && test -f .env.example && test -f README.md
for d in dagu ops generated/spreadsheet-converters sources/spreadsheets sources/rfp \
         import/git import/spreadsheet import/pdf import/jira \
         normalized/requirements normalized/rfp normalized/jira \
         domain/systems domain/subdomains \
         requirements/extracted requirements/mapped requirements/status \
         requirements/conflicts requirements/resolutions \
         output .state/hashes .state/runs; do
  test -d "$d" || { echo "Missing: $d"; exit 1; }
done
```
