# WP-29: Dagu workflow `40-requirements-analysis.yaml` (incl. resolution approval gate)

## Context
Implements spec §11. Runs the full requirements pipeline, with an optional human approval gate before accepting high-impact conflict resolutions.

Prerequisite WPs: WP-18, WP-19, WP-20, WP-21, WP-22, WP-23.

## Scope
### In scope
- `dagu/40-requirements-analysis.yaml` with steps:
  1. `extract` → `python -m ops.agent_requirements_extract`.
  2. `map` → `python -m ops.agent_requirements_mapping` (depends on 1, and on `domain/` already being built).
  3. `status` → `python -m ops.agent_requirements_status` (depends on 2).
  4. `detect_conflicts` → `python -m ops.agent_conflict_detection` (depends on 3).
  5. `propose_resolutions` → `python -m ops.agent_conflict_resolutions` (depends on 4).
  6. `approve_resolutions` — **human approval step**. Approval only required for resolutions with `criticality: high`. Configure the workflow to surface those resolutions and pause; lower-criticality items can pass through.
  7. `roadmap` → `python -m ops.agent_roadmap` (depends on 3 and 5).
  8. Validation gate.

### Out of scope
- Final report (WP-30).

## Inputs
- All outputs from WP-26 and WP-28.

## Outputs / Deliverables
- `dagu/40-requirements-analysis.yaml`.

## Implementation notes
- The approval gate (step 6) is described in spec §3.5 and §16 as required for high-impact resolutions. Implementation strategy is the same as WP-26/WP-28.
- Validation must happen after every step that produces a YAML, not only at the end, so a failure surfaces early.

## Acceptance criteria
- [ ] `dagu validate` exits 0.
- [ ] All requirements artifacts exist and validate after a successful run.
- [ ] Workflow blocks at step 6 if any high-criticality resolution lacks approval.

## Verification commands
```bash
dagu start dagu/40-requirements-analysis.yaml
python -m ops.validate_artifacts validate all
```

## Open questions
- Threshold for required approval: hard-code `criticality: high` or make it configurable? Default: hard-code; revisit later.
