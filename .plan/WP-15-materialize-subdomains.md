# WP-15: Materialize subdomain folders (`ops/materialize_domain_boundaries.py`)

## Context
Implements spec §10.4.2. After human approval of `domain/suggested-boundaries.yaml`, materialize the subdomain folders. The spec mandates the conservative approach: **do not move** system summaries; create subdomain index files that *reference* them.

Prerequisite WPs: WP-14.

## Scope
### In scope
- CLI: `python -m ops.materialize_domain_boundaries [--yaml domain/suggested-boundaries.yaml]`.
- Validate input via the WP-14 schema before doing anything.
- For each subdomain:
  - Create `domain/subdomains/<name>/`.
  - Write `domain/subdomains/<name>/systems.yaml`:
    ```yaml
    systems:
      - ../../systems/billing-service.md
      - ../../systems/invoice-reconciliation.md
    ```
  - Do **not** create the `<name>.md` here — that is WP-16's job.
  - Do **not** delete or move anything under `domain/systems/`.
- Detect and report removed subdomains: if a folder under `domain/subdomains/` no longer corresponds to a name in the YAML, leave it on disk but log a warning. (Removal is a destructive operation; defer to a separate `--prune` flag.)
- Detect renamed subdomains via heuristic (same `systems:` list, different `name`); log but do not auto-rename.
- Add an approval-receipt file `domain/subdomains/.approved-from.yaml` recording:
  ```yaml
  approved_yaml: domain/suggested-boundaries.yaml
  approved_yaml_sha256: <hash>
  materialized_at: ...
  ```
  Subsequent runs require the input YAML's hash to differ before re-materializing, unless `--force`.

### Out of scope
- Subdomain summaries (WP-16).
- Pruning removed subdomains (later WP).

## Inputs
- `domain/suggested-boundaries.yaml` (approved version).
- `domain/systems/*.md`.

## Outputs / Deliverables
- `ops/materialize_domain_boundaries.py`
- `domain/subdomains/<name>/systems.yaml` per subdomain.
- `domain/subdomains/.approved-from.yaml`.
- `schemas/subdomain-systems.schema.json` + validator entry.
- Tests.

## Implementation notes
- Language: **Python**.
- This script is deterministic; no agent involvement.
- All writes are atomic; never leave a half-written `systems.yaml`.

## Acceptance criteria
- [ ] Given a valid boundaries YAML, the script creates the right folder structure and `systems.yaml` files.
- [ ] Re-running with the same input is a no-op (verified via hash receipt).
- [ ] Removing a subdomain from the YAML leaves the folder but logs a warning.
- [ ] Running against an invalid YAML exits non-zero before touching the filesystem.
- [ ] `python -m ops.validate_artifacts validate all` passes.

## Verification commands
```bash
python -m ops.materialize_domain_boundaries
python -m pytest -q tests/test_materialize_domain_boundaries.py
python -m ops.validate_artifacts validate all
```

## Open questions
- Should `systems.yaml` use absolute repo-root paths instead of relative? Spec uses relative; keep relative for portability.
