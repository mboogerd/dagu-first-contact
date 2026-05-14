# WP-02: Frontmatter & artifact-metadata helper

## Context
Spec §14 mandates frontmatter on generated artifacts for traceability, debugging, and future incremental recomputation. Many later WPs (every importer, every agent step) need to read and write this frontmatter consistently. A tiny shared helper avoids divergence.

Prerequisite WPs: WP-01.

## Scope
### In scope
- Define the canonical frontmatter schema (YAML inside `---` fences) covering at minimum:
  - `artifact_type` (enum, see spec — system-summary, subdomain-summary, domain-summary, requirement-extract, requirements-mapping, requirements-status, conflicts, resolutions, roadmap, rfp-normalized, jira-normalized, requirements-normalized, interactions, suggested-boundaries, import-manifest, final-report)
  - `generated_by` (workflow id, e.g. `20-domain-analysis`)
  - `generated_at` (RFC 3339 UTC)
  - `inputs` (list of paths relative to repo root)
  - `input_hashes` (mapping path → content hash; for directories use a recursive hash)
  - `confidence` (enum: `high | medium | low | unknown`) — optional for deterministic artifacts
  - free-form additional keys allowed
- Provide a Python helper module `ops/_artifact.py` with at minimum:
  - `read_frontmatter(path) -> tuple[dict, str]`
  - `write_artifact(path, frontmatter: dict, body: str)` (atomic write)
  - `hash_path(path) -> str` (file: sha256; dir: hash of sorted tree of `(relpath, sha256)`)
  - `now_iso()` returning UTC RFC 3339
  - `enforce_required_keys(frontmatter, required: list[str])`
- Provide a JSON Schema (`schemas/frontmatter.schema.json`) for the frontmatter dict, callable from the validator (WP-03).
- Tests (`tests/test_artifact.py`) covering: round-trip read/write, atomicity (no partial file on crash — simulate via `tmp_path`), directory hashing stability, schema validation.

### Out of scope
- Implementing artifact-specific schemas (those belong to the WP that introduces the artifact).
- Generic "validate all artifacts" logic (WP-03).

## Inputs
- Spec §14.

## Outputs / Deliverables
- `ops/_artifact.py`
- `schemas/frontmatter.schema.json`
- `tests/test_artifact.py`
- `pyproject.toml` (or `requirements-dev.txt`) updated with `pyyaml`, `jsonschema`, `pytest`.
- Short doc snippet in top-level `README.md` (or `ops/README.md`) summarising the convention with an example.

## Implementation notes
- Language: **Python**. The spec names `ops/*.py` and later importers / converters will share this helper.
- The leading underscore on `_artifact.py` signals "private to `ops/`"; later modules import it relatively (`from ._artifact import ...`) — this means `ops/` must be a Python package (`ops/__init__.py`).
- Use `ruamel.yaml` if frontmatter round-trip preservation matters; `pyyaml` is fine for write-only. Pick one; record the choice.
- Atomic write = write to `path + ".tmp"` then `os.replace`.
- Directory hashing must be stable across machines (sort paths, ignore `.DS_Store` and `__pycache__`).

## Acceptance criteria
- [ ] `python -m pytest tests/test_artifact.py` passes.
- [ ] `python -c "from ops._artifact import write_artifact, read_frontmatter, hash_path, now_iso"` succeeds.
- [ ] `jsonschema -i <(echo '{"artifact_type":"system-summary","generated_by":"x","generated_at":"2026-05-14T12:00:00Z","inputs":[],"input_hashes":{}}') schemas/frontmatter.schema.json` succeeds.
- [ ] Schema rejects a missing `artifact_type`.
- [ ] Hashing two identical trees produces identical hashes; modifying one file changes the hash.
- [ ] (human review) Helper API is small (≤ ~10 public functions) and documented.

## Verification commands
```bash
python -m pytest -q tests/test_artifact.py
python -c "from ops._artifact import write_artifact, read_frontmatter, hash_path, now_iso; print('ok')"
```

## Open questions
- Should `inputs` allow globs, or only resolved paths? Recommendation: resolved paths only; the producer resolves globs before writing.
- Hashing large `import/git/*` trees may be slow — should we cache hashes in `.state/hashes/`? Defer until perf becomes a problem.
