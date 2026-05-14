# WP-26: Dagu workflow `10-normalize.yaml` (incl. converter approval gate)

## Context
Implements spec §8. Runs deterministic normalization and the spreadsheet converter generation + approval gate.

Prerequisite WPs: WP-08, WP-09, WP-10, WP-11.

## Scope
### In scope
- `dagu/10-normalize.yaml` with logical steps:
  1. `normalize_jira` → `python -m ops.jira_json_to_markdown` (no deps on others).
  2. `generate_spreadsheet_converters` → `python -m ops.agent_generate_spreadsheet_converters`.
  3. `approve_spreadsheet_converters` — **human approval step**. The step pauses until a human approves; on approval, the workflow writes/updates `generated/spreadsheet-converters/.approved.yaml`. Implementation options to evaluate at pickup:
     - Dagu's built-in approval/confirm step (preferred if present in the installed version).
     - A "wait for file" step that polls until `.approved.yaml` has a current entry for each newly generated converter (the human edits the file manually).
     Document the chosen approach.
  4. `run_spreadsheet_converters` → `python -m ops.run_spreadsheet_converters` (depends on step 3).
  5. `normalize_rfp` → `python -m ops.agent_rfp_to_markdown` (no deps on 1–4).
- Validation gate at the end: `python -m ops.validate_artifacts validate all` must pass; if not, the workflow fails.

### Out of scope
- Domain analysis (WP-27).

## Inputs
- Everything under `import/` (produced by WP-25).
- Human attention for step 3.

## Outputs / Deliverables
- `dagu/10-normalize.yaml`.

## Implementation notes
- Confirm Dagu version + approval-step capabilities.
- The approval step must be **idempotent re-runnable**: if all converters are already approved with current hashes, skip the wait.

## Acceptance criteria
- [ ] `dagu validate dagu/10-normalize.yaml` exits 0.
- [ ] Workflow blocks at the approval step when a new/changed converter is detected.
- [ ] Workflow does not block when all converters are already approved.
- [ ] Validator gate fails the workflow if any artifact is invalid.

## Verification commands
```bash
dagu start dagu/10-normalize.yaml
```

## Open questions
- If Dagu doesn't have a first-class approval primitive, the "wait for file" approach is acceptable but should clearly surface the pending list (e.g. via a step that prints which converters need approval and the exact command to approve them).
