# WP-19: Requirements mapping (agent) + schema

## Context
Implements spec §11.4.2. Maps extracted requirements to systems and subdomains, with rationale, evidence, and confidence.

Prerequisite WPs: WP-18, WP-17.

## Scope
### In scope
- Driver `ops/agent_requirements_mapping.py`:
  - Inputs: `requirements/extracted/requirements.yaml`, `domain/domain.md`, `domain/subdomains/**/*.md`, `domain/systems/*.md`, `domain/interactions.md`.
  - Calls agent (`prompts/requirements-mapping.md`).
  - Produces:
    - `requirements/mapped/requirements-mapping.yaml`:
      ```yaml
      mappings:
        - requirement_id: REQ-0001
          affected_systems: [billing-service]
          affected_subdomains: [billing]
          rationale: >
            ...
          evidence:
            - domain/systems/billing-service.md
          confidence: medium
          unknowns: []
      ```
    - `requirements/mapped/requirements-by-system.md` and `requirements/mapped/requirements-by-subdomain.md` — pivoted views. The driver renders these deterministically from the YAML (do not ask the agent for them).
- Both `.md` views have frontmatter:
  ```yaml
  artifact_type: requirements-mapping
  generated_by: 40-requirements-analysis
  ...
  ```
- Add `schemas/requirements-mapping.schema.json` + validator. Validator cross-checks: every `requirement_id` exists in extracted requirements; every `affected_systems` value exists in `domain/systems/`; every `affected_subdomains` value exists in `domain/subdomains/`.

### Out of scope
- Status classification (WP-20).

## Inputs
- `requirements/extracted/requirements.yaml`.
- All `domain/**/*.md`.
- `prompts/requirements-mapping.md`.

## Outputs / Deliverables
- `ops/agent_requirements_mapping.py`
- `prompts/requirements-mapping.md`
- `schemas/requirements-mapping.schema.json` + validator
- Three output files under `requirements/mapped/`.
- Tests with a stubbed agent.

## Implementation notes
- Language: **Python**.
- The pivoted markdown views are deterministic — write them in the driver, not in the prompt.
- A requirement may map to zero systems if it is purely organisational; allow empty lists and capture that in `unknowns`.

## Acceptance criteria
- [ ] Mapping YAML validates and references only known requirements/systems/subdomains.
- [ ] Pivoted views are reproducible from the YAML (snapshot test).
- [ ] Re-running with no changes is a no-op.

## Verification commands
```bash
python -m pytest -q tests/test_agent_requirements_mapping.py
python -m ops.validate_artifacts validate all
```

## Open questions
- None significant.
