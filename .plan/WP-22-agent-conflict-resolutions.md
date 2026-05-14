# WP-22: Conflict resolutions (agent) + schema

## Context
Implements spec §11.4.5. Proposes resolutions for detected conflicts. Output may feed an approval gate in WP-29.

Prerequisite WPs: WP-21.

## Scope
### In scope
- Driver `ops/agent_conflict_resolutions.py`:
  - Inputs: `requirements/conflicts/conflicts.yaml`, `domain/domain.md`, `domain/subdomains/**/*.md`.
  - Calls agent (`prompts/conflict-resolutions.md`).
  - Produces:
    - `requirements/resolutions/resolutions.yaml`:
      ```yaml
      resolutions:
        - id: RES-0001
          conflict_id: CONF-0001
          recommended_resolution: >
            ...
          alternatives:
            - ...
          trade_offs: ...
          criticality: high
          confidence: medium
          affected_systems: [billing-service]
          affected_teams: [billing]
          required_human_decisions:
            - ...
      ```
    - `requirements/resolutions/resolutions.md` (frontmatter `artifact_type: resolutions`).
- Add `schemas/resolutions.schema.json` + validator. Validator enforces that every `conflict_id` exists.
- Stable IDs across re-runs.

### Out of scope
- Roadmap (WP-23).

## Inputs
- `requirements/conflicts/conflicts.yaml`.
- Domain summaries.
- `prompts/conflict-resolutions.md`.

## Outputs / Deliverables
- `ops/agent_conflict_resolutions.py`
- `prompts/conflict-resolutions.md`
- `schemas/resolutions.schema.json` + validator
- Output YAML and MD.
- Tests with a stubbed agent.

## Implementation notes
- Language: **Python**.
- This is one of the explicit human-approval gates (spec §16). The driver itself does not gate; the Dagu workflow (WP-29) does.

## Acceptance criteria
- [ ] Output validates; every conflict has at least one resolution proposal.
- [ ] IDs are stable across re-runs.
- [ ] Re-running with no changes is a no-op.

## Verification commands
```bash
python -m pytest -q tests/test_agent_conflict_resolutions.py
python -m ops.validate_artifacts validate all
```

## Open questions
- Multiple resolutions per conflict? Default: 1 recommended + N alternatives in the same record.
