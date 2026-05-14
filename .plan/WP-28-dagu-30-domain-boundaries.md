# WP-28: Dagu workflow `30-domain-boundaries.yaml` (incl. boundary approval gate)

## Context
Implements spec §10. Handles approval, materialization, subdomain summaries, and the root domain summary.

Prerequisite WPs: WP-15, WP-16, WP-17.

## Scope
### In scope
- `dagu/30-domain-boundaries.yaml` with steps:
  1. `approve_boundaries` — **human approval step** on `domain/suggested-boundaries.yaml`. The user may edit the YAML before approval. On approval, the workflow records the approved hash in `domain/subdomains/.approved-from.yaml` (or instructs WP-15's script to do so).
  2. `materialize` → `python -m ops.materialize_domain_boundaries` (depends on 1).
  3. `subdomain_summaries` → `python -m ops.agent_subdomain_summary` (depends on 2). May fan out per subdomain.
  4. `root_domain_summary` → `python -m ops.agent_root_domain_summary` (depends on 3).
  5. Validation gate.

### Out of scope
- Requirements analysis (WP-29).

## Inputs
- All outputs from WP-27.

## Outputs / Deliverables
- `dagu/30-domain-boundaries.yaml`.

## Implementation notes
- Same approval-step considerations as WP-26.
- If the user edits the YAML in-place, the workflow must re-validate it before proceeding.

## Acceptance criteria
- [ ] Workflow blocks at step 1 when the suggested-boundaries hash differs from the last approved hash.
- [ ] `domain/subdomains/**/*.md` and `domain/domain.md` exist and validate after a successful run.
- [ ] Re-running without changes does not re-materialize or re-summarise (idempotent).

## Verification commands
```bash
dagu start dagu/30-domain-boundaries.yaml
python -m ops.validate_artifacts validate all
```

## Open questions
- None significant.
