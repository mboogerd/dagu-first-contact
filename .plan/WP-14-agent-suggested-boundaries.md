# WP-14: Suggested domain boundaries (agent) + schema

## Context
Implements spec §9.4.3. Proposes a subdomain hierarchy over the systems based on summaries and interactions. Output feeds the approval gate in WP-28.

Prerequisite WPs: WP-12, WP-13, WP-03.

## Scope
### In scope
- Driver `ops/agent_suggested_boundaries.py`:
  - Reads `domain/systems/*.md` and `domain/interactions.md`.
  - Calls the agent (`prompts/suggested-boundaries.md`) to produce:
    - `domain/suggested-boundaries.md` — narrative with rationale per cluster.
    - `domain/suggested-boundaries.yaml` — machine-readable, matching spec §9.4.3:
      ```yaml
      subdomains:
        - name: billing
          systems: [billing-service, invoice-reconciliation]
          rationale: >
            ...
          confidence: high
      ```
  - Frontmatter on the markdown:
    ```yaml
    artifact_type: suggested-boundaries
    generated_by: 20-domain-analysis
    generated_at: ...
    inputs: [domain/systems/..., domain/interactions.md]
    input_hashes: { ... }
    confidence: ...
    ```
- Add `schemas/suggested-boundaries.schema.json` + validator plug-in (WP-03):
  - Required: `subdomains: [{ name, systems, rationale, confidence }]`.
  - `name` must be unique; `systems` must be non-empty; every entry in `systems` must exist as `domain/systems/<name>.md` (cross-refs check from WP-03 already covers this).
- Refuse to overwrite the YAML if it has been hand-edited *and* has no `regenerate: true` marker — detect by comparing the stored `input_hashes` with current values *and* checking a sentinel `# edited-by-human` comment line. Document the behaviour clearly.

### Out of scope
- Materialization (WP-15).
- Subdomain summaries (WP-16).

## Inputs
- `domain/systems/*.md`.
- `domain/interactions.md`.
- `prompts/suggested-boundaries.md`.

## Outputs / Deliverables
- `ops/agent_suggested_boundaries.py`
- `prompts/suggested-boundaries.md`
- `schemas/suggested-boundaries.schema.json`
- `ops/validators/suggested_boundaries.py`
- `domain/suggested-boundaries.md`, `domain/suggested-boundaries.yaml`
- Tests with a stubbed agent.

## Implementation notes
- Language: **Python**.
- The YAML is the source of truth for downstream steps. The markdown is for humans.
- Be conservative about overwriting human edits — this is one of the spec's explicit approval gates.

## Acceptance criteria
- [ ] With a stubbed agent, the driver produces both files and they validate.
- [ ] Hand-edited YAML (with the sentinel comment) is preserved across re-runs.
- [ ] Every system in `domain/systems/` is assigned to exactly one subdomain (validator check).
- [ ] `python -m ops.validate_artifacts validate suggested-boundaries` passes/fails as expected.

## Verification commands
```bash
python -m pytest -q tests/test_agent_suggested_boundaries.py
python -m ops.validate_artifacts validate all
```

## Open questions
- Allow a system to belong to multiple subdomains? Default: no (single owner); revisit later.
- Confidence enum: align with frontmatter (`high|medium|low|unknown`).
