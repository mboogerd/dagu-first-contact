# WP-20: Requirements status classification (agent) + schema

## Context
Implements spec §11.4.3. Classifies each mapped requirement into one of: `obsolete | implemented | partially implemented | future | uncertain`. Uses imported code and Jira tickets as evidence.

Prerequisite WPs: WP-19.

## Scope
### In scope
- Driver `ops/agent_requirements_status.py`:
  - Inputs: `requirements/mapped/requirements-mapping.yaml`, `import/git/*`, `normalized/jira/*`, `domain/systems/*.md`.
  - Optional deterministic pre-search per requirement: a code search across the affected systems for key phrases from the requirement (committed under `.state/requirements/status-evidence/<req-id>.json`).
  - Calls agent per requirement (or in batches; pick at pickup) using `prompts/requirements-status.md` enforcing the §11.4.3 fields: `requirement_id, status, rationale, evidence, confidence, affected_systems, affected_subdomains, recommended_follow_up`.
  - Produces:
    - `requirements/status/status.yaml`
    - `requirements/status/status.md` (with frontmatter)
- Add `schemas/requirements-status.schema.json` + validator. Validator enforces the status enum.

### Out of scope
- Conflicts (WP-21).

## Inputs
- All mapping outputs from WP-19.
- `import/git/*`, `normalized/jira/*`, `domain/systems/*.md`.
- `prompts/requirements-status.md`.

## Outputs / Deliverables
- `ops/agent_requirements_status.py`
- `prompts/requirements-status.md`
- `schemas/requirements-status.schema.json` + validator
- `requirements/status/status.yaml`, `requirements/status/status.md`.
- `.state/requirements/status-evidence/*.json`.
- Tests with a stubbed agent.

## Implementation notes
- Language: **Python**.
- Pre-search keeps prompt size manageable on a large codebase. Use `ripgrep` if available; fallback to Python.
- Batching: process requirements grouped by `affected_subdomains` to maximise prompt re-use.

## Acceptance criteria
- [ ] Status YAML validates; every requirement in the mapping has a status entry.
- [ ] Status values are limited to the allowed enum.
- [ ] Re-running with no changes is a no-op.

## Verification commands
```bash
python -m pytest -q tests/test_agent_requirements_status.py
python -m ops.validate_artifacts validate all
```

## Open questions
- Granularity: classify per-requirement or per-(requirement, system) pair? Spec implies per-requirement with system-level breakdown in `affected_systems`. Default: per-requirement with optional per-system notes inside `rationale`.
