# WP-03: Validation tool foundation (`ops/validate_artifacts.py`)

## Context
Spec §15 requires a validation script that runs before major synthesis steps and before final report generation. This WP establishes the validator as a *pluggable* tool. Each later WP that introduces a structured artifact will register its schema with this validator (by dropping a JSON Schema in `schemas/` and a registration entry).

Prerequisite WPs: WP-01, WP-02.

## Scope
### In scope
- `ops/validate_artifacts.py` CLI with sub-commands:
  - `validate references` → validates `references.yaml`
  - `validate frontmatter <path-or-glob>` → validates frontmatter against `schemas/frontmatter.schema.json`
  - `validate all` → runs all registered validators; exits non-zero if any fail
  - `validate <name>` (extensible) — dispatches to a registered validator by name
- A registry mechanism: schemas in `schemas/*.schema.json` + an `ops/validators/` package where each module registers a validator. Adding a new schema in a later WP only requires dropping a new file in `schemas/` and a new module in `ops/validators/`.
- A JSON Schema for `references.yaml` (`schemas/references.schema.json`) matching spec §5: required top-level keys (`git`, optional `spreadsheets`, `rfp`, `jira`); each entry has the fields shown in §5.
- Cross-cutting checks (collected as separate validator entries so they can be invoked individually):
  - broken-file-references: every path mentioned in any frontmatter `inputs:` or `sources:` field exists on disk
  - missing-summaries: every system listed in `domain/suggested-boundaries.yaml` (when present) has a matching `domain/systems/*.md`
  - unknown-system-names: every `affected_systems:` value in requirements artifacts (when present) resolves to a known system
- All checks must degrade gracefully — if a file does not exist yet (e.g. `suggested-boundaries.yaml` before Phase 3), the validator skips that check rather than failing.
- Useful human output (group errors by file; non-zero exit code on failure; `--json` flag for machine output).
- Tests: validator passes on fixtures, fails on intentionally-broken fixtures.

### Out of scope
- Schemas for artifacts not yet introduced (those land in later WPs together with their producers).
- Auto-fix behaviour.

## Inputs
- Spec §5, §14, §15.
- `schemas/frontmatter.schema.json` from WP-02.
- `references.yaml` example from WP-01.

## Outputs / Deliverables
- `ops/validate_artifacts.py`
- `ops/validators/__init__.py` (registry loader)
- `ops/validators/references.py`, `ops/validators/frontmatter.py`, `ops/validators/cross_refs.py`
- `schemas/references.schema.json`
- `tests/test_validate_artifacts.py` with at least one pass and one fail fixture per validator.
- README snippet documenting how later WPs plug in.

## Implementation notes
- Language: **Python**. Reuse `ops/_artifact.py` from WP-02. Use `jsonschema` (Draft 2020-12).
- Use `argparse` or `typer` (pick one; record choice). Keep the dependency surface small.
- Validators should expose a uniform interface:
  ```python
  class Validator(Protocol):
      name: str
      def run(self, repo_root: Path) -> list[ValidationError]: ...
  ```
- The registry can be a simple module-level list populated on import, or `entry_points` — prefer the simple list for now.

## Acceptance criteria
- [ ] `python -m ops.validate_artifacts validate references` on the seed `references.yaml` exits 0.
- [ ] Corrupting `references.yaml` (e.g. removing `url` from a git entry) makes it exit non-zero with a useful error.
- [ ] `python -m ops.validate_artifacts validate all` on a freshly-initialised repo exits 0 (no false positives from missing-but-allowed artifacts).
- [ ] `python -m ops.validate_artifacts --help` lists all registered validators.
- [ ] `python -m pytest tests/test_validate_artifacts.py` passes.
- [ ] Adding a new schema in a hypothetical follow-up requires no edits to `validate_artifacts.py` itself — only adding a file under `ops/validators/` and one under `schemas/`. Demonstrate this in the README snippet.

## Verification commands
```bash
python -m ops.validate_artifacts validate references
python -m ops.validate_artifacts validate all
python -m pytest -q tests/test_validate_artifacts.py
```

## Open questions
- `--json` output shape: borrow from `eslint`-style or roll our own? Recommendation: a minimal `{ "errors": [ { "validator": "...", "path": "...", "message": "..." } ] }`.
