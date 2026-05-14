# WP-21: Conflict detection (agent) + schema

## Context
Implements spec §11.4.4. Detects conflicts among requirements (especially future ones) and records them.

Prerequisite WPs: WP-20.

## Scope
### In scope
- Driver `ops/agent_conflict_detection.py`:
  - Inputs: `requirements/extracted/requirements.yaml`, `requirements/mapped/requirements-mapping.yaml`, `requirements/status/status.yaml`.
  - Calls agent (`prompts/conflict-detection.md`).
  - Produces:
    - `requirements/conflicts/conflicts.yaml`:
      ```yaml
      conflicts:
        - id: CONF-0001
          involved_requirements: [REQ-0001, REQ-0042]
          affected_systems: [billing-service]
          affected_subdomains: [billing]
          nature: >
            ...
          criticality: high   # high|medium|low
          confidence: medium
          evidence:
            - requirements/extracted/requirements.yaml
          possible_resolution_directions:
            - ...
      ```
    - `requirements/conflicts/conflicts.md` (frontmatter `artifact_type: conflicts`).
- Add `schemas/conflicts.schema.json` + validator. Validator enforces:
  - all `involved_requirements` exist in extracted requirements
  - `criticality` enum
  - stable IDs across re-runs (use a sequence file just like WP-18)

### Out of scope
- Resolutions (WP-22).

## Inputs
- All requirements/* artifacts produced so far.
- `prompts/conflict-detection.md`.

## Outputs / Deliverables
- `ops/agent_conflict_detection.py`
- `prompts/conflict-detection.md`
- `schemas/conflicts.schema.json` + validator
- Output YAML and MD.
- `.state/requirements/conflict-id-sequence.yaml`.
- Tests with a stubbed agent.

## Implementation notes
- Language: **Python**.
- Encourage pairwise reasoning in the prompt but allow N-way conflicts.

## Acceptance criteria
- [ ] Output validates; every referenced requirement exists.
- [ ] Conflict IDs are stable across re-runs.
- [ ] Re-running with no changes is a no-op.

## Verification commands
```bash
python -m pytest -q tests/test_agent_conflict_detection.py
python -m ops.validate_artifacts validate all
```

## Open questions
- Naming: should we distinguish "conflict" vs "tension"? Default: single category for MVP.
