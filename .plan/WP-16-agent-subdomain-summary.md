# WP-16: Subdomain summary (agent)

## Context
Implements spec §10.4.3. For each materialized subdomain, produce `domain/subdomains/<name>/<name>.md`.

Prerequisite WPs: WP-15.

## Scope
### In scope
- Driver `ops/agent_subdomain_summary.py`:
  - For each `domain/subdomains/<name>/systems.yaml`:
    - Read the referenced system summaries.
    - Read `domain/interactions.md` (for internal/external split).
    - Call agent with `prompts/subdomain-summary.md`. Prompt enforces sections from §10.4.3: `purpose, included systems, roles and responsibilities, internal interactions, external interactions, ownership hints, requirement relevance (if known), evidence gaps, confidence`.
    - Write `domain/subdomains/<name>/<name>.md` via `write_artifact` with:
      ```yaml
      artifact_type: subdomain-summary
      generated_by: 30-domain-boundaries
      generated_at: ...
      inputs: [domain/subdomains/<name>/systems.yaml, domain/interactions.md, <linked system summaries>]
      input_hashes: { ... }
      subdomain: <name>
      confidence: ...
      ```
- Idempotent on unchanged inputs.

### Out of scope
- Root domain summary (WP-17).

## Inputs
- `domain/subdomains/<name>/systems.yaml`.
- `domain/systems/*.md`.
- `domain/interactions.md`.
- `prompts/subdomain-summary.md`.

## Outputs / Deliverables
- `ops/agent_subdomain_summary.py`
- `prompts/subdomain-summary.md`
- `domain/subdomains/<name>/<name>.md`.
- Tests with a stubbed agent.

## Implementation notes
- Language: **Python**.
- Process subdomains in parallel only if `ops/_agent.py` supports it; default sequential for predictability.

## Acceptance criteria
- [ ] For each subdomain folder, exactly one `<name>.md` is created with valid frontmatter.
- [ ] Re-running with no changes is a no-op.
- [ ] If `systems.yaml` references a missing system summary, the driver fails clearly.

## Verification commands
```bash
python -m pytest -q tests/test_agent_subdomain_summary.py
python -m ops.validate_artifacts validate frontmatter "domain/subdomains/*/*.md"
```

## Open questions
- None significant.
