# WP-31: Dagu `main.yaml` orchestration

## Context
Implements spec §6.1. Top-level workflow that strings together import → normalize → domain analysis → boundary approval → requirements analysis → final report.

Prerequisite WPs: WP-25..WP-30.

## Scope
### In scope
- `dagu/main.yaml` with the dependency graph shown in spec §6.1:
  ```
  import → normalize → domain_analysis → domain_boundaries
                                       ↘
                                         requirements_analysis → final_report
                                       ↗
                            normalize ─┘
  ```
- Each top-level step `run:`s the corresponding sub-workflow (`00-import.yaml`, etc.).
- The workflow surfaces a clear "where we paused" status when any approval step blocks.
- A `--mode quick` or parameter that skips heavy steps (for development) is **not** in scope here; introduce as a follow-up WP if useful.

### Out of scope
- Sidecar watcher integration (WP-33).

## Inputs
- All sub-workflow files.

## Outputs / Deliverables
- `dagu/main.yaml`.

## Implementation notes
- Confirm Dagu's `run:` semantics for sub-workflow invocation in the installed version. The spec gives a logical shape; the exact YAML may differ.

## Acceptance criteria
- [ ] `dagu validate dagu/main.yaml` exits 0.
- [ ] A full run against the WP-32 fixtures (with approvals granted) produces all expected artifacts and a final report.
- [ ] Re-running `main.yaml` with no input changes is largely a no-op (each sub-step honours its idempotency contract).

## Verification commands
```bash
dagu start dagu/main.yaml
```

## Open questions
- Does Dagu treat sub-workflow failures as fatal by default? Confirm and document.
