# WP-30: Dagu workflow `90-final-report.yaml` (incl. publish approval gate)

## Context
Implements spec §12 as a Dagu workflow. Includes the publish/export approval gate from §3.5 and §16.

Prerequisite WPs: WP-24.

## Scope
### In scope
- `dagu/90-final-report.yaml` with steps:
  1. `validate_inputs` → `python -m ops.validate_artifacts validate all` (fail-fast).
  2. `generate` → `python -m ops.agent_final_report`.
  3. `approve_publish` — **human approval step** on `output/final-report.md`. Approval records to `output/.published.yaml`:
     ```yaml
     report_sha256: <hash>
     approved_at: ...
     approved_by: ...
     ```
  4. `publish` (placeholder for now) — copies `output/final-report.md` to `output/published/final-report-<timestamp>.md`. Real publishing (e.g. upload to Confluence) is a future WP.

### Out of scope
- PDF/DOCX rendering (spec §12.3 lists as optional future).
- Real publication backends.

## Inputs
- All artifacts produced by the prior workflows.

## Outputs / Deliverables
- `dagu/90-final-report.yaml`.

## Implementation notes
- Same approval-step strategy as the other workflows.

## Acceptance criteria
- [ ] `dagu validate` exits 0.
- [ ] After approval, a timestamped snapshot exists under `output/published/`.
- [ ] Re-running without changes does not produce duplicate snapshots.

## Verification commands
```bash
dagu start dagu/90-final-report.yaml
```

## Open questions
- Snapshot retention: keep N latest? Default: keep all for MVP.
