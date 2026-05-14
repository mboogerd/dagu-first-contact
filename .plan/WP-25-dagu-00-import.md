# WP-25: Dagu workflow `00-import.yaml`

## Context
Implements spec §7 as a Dagu workflow that orchestrates all importers from WP-04..WP-07.

Prerequisite WPs: WP-04, WP-05, WP-06, WP-07.

## Scope
### In scope
- `dagu/00-import.yaml` invoking each importer:
  - `import_git` → `python -m ops.import_git`
  - `import_spreadsheets` → `python -m ops.import_spreadsheets`
  - `import_pdfs` → `python -m ops.import_pdfs`
  - `import_jira` → `python -m ops.import_jira`
- All four steps run independently (no inter-dependencies) and report success/failure individually.
- Logging routes to Dagu's standard log handling; the workflow does not write its own logs to `.state/`.
- Each step retries up to 3× on transient failure (network), but does not retry on validation failures.
- The workflow declares `references.yaml` as an input parameter (so callers can pass an alternate references file for testing).

### Out of scope
- Triggering normalize/etc. (that's `main.yaml`, WP-31).

## Inputs
- `references.yaml`, environment variables.

## Outputs / Deliverables
- `dagu/00-import.yaml`.
- Documentation of how to launch this workflow standalone (`dagu start dagu/00-import.yaml`).

## Implementation notes
- At pickup time, confirm the installed Dagu version and adjust YAML syntax accordingly. The spec acknowledges syntax may vary.
- Prefer `executor: command` with explicit `python -m ops.<module>` invocations so steps can be re-run locally without Dagu.
- Pass `references.yaml` path via a Dagu parameter; default to `./references.yaml`.

## Acceptance criteria
- [ ] `dagu validate dagu/00-import.yaml` (or equivalent in the installed Dagu) exits 0.
- [ ] Running the workflow against the fixtures from WP-32 populates `import/`.
- [ ] Each step's logs are visible in the Dagu UI.

## Verification commands
```bash
dagu start dagu/00-import.yaml --params="references=tests/fixtures/references-local.yaml"
```

## Open questions
- Should retries vary per importer? Default: same policy for MVP.
