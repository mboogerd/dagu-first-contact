# WP-23: Roadmap synthesis (agent) + schema

## Context
Implements spec §11.4.6. Organises future work into a hierarchical roadmap.

Prerequisite WPs: WP-20, WP-22.

## Scope
### In scope
- Driver `ops/agent_roadmap.py`:
  - Inputs: `requirements/status/status.yaml`, `requirements/resolutions/resolutions.yaml`, `domain/domain.md`, `domain/subdomains/**/*.md`.
  - Calls agent (`prompts/roadmap.md`).
  - Produces:
    - `requirements/roadmap.yaml`:
      ```yaml
      roadmap:
        - subdomain: billing
          systems:
            - name: billing-service
              themes:
                - name: invoice-reconciliation-v2
                  requirements: [REQ-0001, REQ-0042]
                  dependencies: []
                  confidence: medium
                  criticality: high
      ```
    - `requirements/roadmap.md` (frontmatter `artifact_type: roadmap`).
- Add `schemas/roadmap.schema.json` + validator. Cross-check: every requirement listed exists with status `future` or `partially implemented`.

### Out of scope
- Final report (WP-24).

## Inputs
- All requirements YAMLs above.
- Domain summaries.
- `prompts/roadmap.md`.

## Outputs / Deliverables
- `ops/agent_roadmap.py`
- `prompts/roadmap.md`
- `schemas/roadmap.schema.json` + validator
- Output YAML and MD.
- Tests with a stubbed agent.

## Implementation notes
- Language: **Python**.

## Acceptance criteria
- [ ] Output validates.
- [ ] Every roadmap requirement has status `future` or `partially implemented`.
- [ ] Re-running with no changes is a no-op.

## Verification commands
```bash
python -m pytest -q tests/test_agent_roadmap.py
python -m ops.validate_artifacts validate all
```

## Open questions
- Should roadmap include `obsolete` items as "remove" themes? Default: no — roadmap is forward-looking; obsoletes are noted in the final report.
