# WP-27: Dagu workflow `20-domain-analysis.yaml`

## Context
Implements spec §9. Produces system summaries, interaction model, and suggested boundaries.

Prerequisite WPs: WP-12, WP-13, WP-14.

## Scope
### In scope
- `dagu/20-domain-analysis.yaml` with steps:
  1. `system_summaries` → `python -m ops.agent_system_summary`. Can fan out per repo (Dagu parallel steps) — pick at pickup.
  2. `interaction_model` → `python -m ops.agent_interaction_model` (depends on 1).
  3. `suggested_boundaries` → `python -m ops.agent_suggested_boundaries` (depends on 2).
  4. Validation gate at the end.

### Out of scope
- Approval of boundaries (WP-28).

## Inputs
- `import/git/*` and their manifests.
- `normalized/jira/*` (optional input for system summaries).

## Outputs / Deliverables
- `dagu/20-domain-analysis.yaml`.

## Implementation notes
- Fan-out per repo gives parallelism but multiplies cost — evaluate at pickup based on the agent integration chosen in WP-12.

## Acceptance criteria
- [ ] `dagu validate` exits 0.
- [ ] After a successful run, `domain/systems/*.md`, `domain/interactions.{md,puml}`, `domain/suggested-boundaries.{md,yaml}` exist and validate.

## Verification commands
```bash
dagu start dagu/20-domain-analysis.yaml
python -m ops.validate_artifacts validate all
```

## Open questions
- None significant.
