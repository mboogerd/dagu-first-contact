# WP-24: Final report (agent)

## Context
Implements spec §12. Consolidates everything into `output/final-report.md`.

Prerequisite WPs: WP-17, WP-23 (and transitively everything else).

## Scope
### In scope
- Driver `ops/agent_final_report.py`:
  - Inputs: `domain/domain.md`, `domain/interactions.md`, `domain/interactions.puml`, `domain/subdomains/**/*.md`, `requirements/status/status.md`, `requirements/conflicts/conflicts.md`, `requirements/resolutions/resolutions.md`, `requirements/roadmap.md`.
  - Calls agent (`prompts/final-report.md`) to synthesise the report. Prompt enforces §12.4.1's section list:
    `executive summary, source overview, current system/domain landscape, system interaction model, ownership/team hints, domain/subdomain hierarchy, requirements landscape, requirement status assessment, future work organization, requirement conflicts, proposed resolutions, critical risks, confidence and evidence gaps, recommended next steps`.
  - Writes `output/final-report.md` via `write_artifact`:
    ```yaml
    artifact_type: final-report
    generated_by: 90-final-report
    generated_at: ...
    inputs: [domain/..., requirements/...]
    input_hashes: { ... }
    confidence: ...
    ```
- Optional: copy `domain/interactions.puml` to `output/diagrams/interactions.puml` for convenience.

### Out of scope
- PDF/DOCX rendering (note as future work in spec §12.3).
- Publication workflow (WP-30 covers the approval gate).

## Inputs
- All synthesis outputs from previous WPs.
- `prompts/final-report.md`.

## Outputs / Deliverables
- `ops/agent_final_report.py`
- `prompts/final-report.md`
- `output/final-report.md`.
- (Optional) `output/diagrams/interactions.puml`.
- Tests with a stubbed agent.

## Implementation notes
- Language: **Python**.
- Input size is significant; chunked synthesis (per section) followed by an integration pass is recommended. Define in the prompt template.

## Acceptance criteria
- [ ] Final report file is produced with valid frontmatter.
- [ ] All §12.4.1 section headings are present.
- [ ] Re-running with no changes is a no-op.

## Verification commands
```bash
python -m pytest -q tests/test_agent_final_report.py
python -m ops.validate_artifacts validate frontmatter output/final-report.md
```

## Open questions
- Section ordering: follow spec verbatim; allow override via prompt config later.
