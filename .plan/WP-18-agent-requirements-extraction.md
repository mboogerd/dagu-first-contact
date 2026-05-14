# WP-18: Requirements extraction (agent) + schema

## Context
Implements spec §11.4.1. Extracts candidate requirements from normalized inputs into a structured YAML and a human-readable markdown.

Prerequisite WPs: WP-08, WP-10, WP-11, WP-03.

## Scope
### In scope
- Driver `ops/agent_requirements_extract.py`:
  - Inputs: `normalized/requirements/*.md`, `normalized/rfp/*.md`, `normalized/jira/**/*.md`.
  - Calls agent (`prompts/requirements-extract.md`).
  - Produces:
    - `requirements/extracted/requirements.yaml` matching spec §11.4.1:
      ```yaml
      requirements:
        - id: REQ-0001
          title: ...
          type: functional   # or non-functional, constraint, business-rule
          description: >
            ...
          sources:
            - normalized/rfp/main-rfp.md#page-12
            - normalized/jira/BILLING/BILLING-123.md
          confidence: high
      ```
    - `requirements/extracted/requirements.md` with frontmatter:
      ```yaml
      artifact_type: requirement-extract
      generated_by: 40-requirements-analysis
      generated_at: ...
      inputs: [normalized/...]
      input_hashes: { ... }
      confidence: ...
      ```
- ID stability: pre-compute IDs deterministically (e.g. `REQ-<sha256-prefix-of-canonicalized-text>` or a sequence file `.state/requirements/id-sequence.yaml`). The agent proposes content; the driver assigns IDs. Picking a strategy at pickup; recommendation: maintain a sequence file mapping `content_hash → id` so re-runs keep IDs stable.
- Add `schemas/requirements.schema.json` + validator (WP-03).

### Out of scope
- Mapping to systems (WP-19).

## Inputs
- All `normalized/**/*.md`.
- `prompts/requirements-extract.md`.

## Outputs / Deliverables
- `ops/agent_requirements_extract.py`
- `prompts/requirements-extract.md`
- `schemas/requirements.schema.json` + `ops/validators/requirements.py`
- `requirements/extracted/requirements.yaml`, `requirements/extracted/requirements.md`
- `.state/requirements/id-sequence.yaml`.
- Tests with a stubbed agent.

## Implementation notes
- Language: **Python**.
- Large input sets may need chunking. Define the strategy in the prompt template.
- Source references use `path#anchor` form so they round-trip in markdown viewers.

## Acceptance criteria
- [ ] Output YAML validates against the schema.
- [ ] IDs are stable across re-runs when content is unchanged.
- [ ] New content produces new IDs without colliding.
- [ ] `python -m ops.validate_artifacts validate requirements` passes.

## Verification commands
```bash
python -m pytest -q tests/test_agent_requirements_extract.py
python -m ops.validate_artifacts validate all
```

## Open questions
- Allow Jira-issue-key-as-requirement-id (e.g. `BILLING-123`)? Default: no — keep `REQ-####` as the canonical id, and record `external_refs` in the YAML.
