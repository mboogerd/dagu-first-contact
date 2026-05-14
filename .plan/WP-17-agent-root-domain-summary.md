# WP-17: Root domain summary (agent)

## Context
Implements spec §10.4.4. Synthesises a top-level summary at `domain/domain.md` from the subdomain summaries and interactions.

Prerequisite WPs: WP-16.

## Scope
### In scope
- Driver `ops/agent_root_domain_summary.py`:
  - Reads `domain/subdomains/*/*.md` and `domain/interactions.md`.
  - Calls agent with `prompts/root-domain-summary.md`. Prompt enforces §10.4.4 sections: `overall system landscape, subdomain overview, cross-subdomain interactions, architectural risks, ownership patterns, open questions, confidence assessment`.
  - Writes `domain/domain.md` via `write_artifact`:
    ```yaml
    artifact_type: domain-summary
    generated_by: 30-domain-boundaries
    generated_at: ...
    inputs: [domain/subdomains/.../<name>.md, domain/interactions.md]
    input_hashes: { ... }
    confidence: ...
    ```
- Idempotent on unchanged inputs.

### Out of scope
- Requirements (WP-18+).

## Inputs
- `domain/subdomains/*/*.md`.
- `domain/interactions.md`.
- `prompts/root-domain-summary.md`.

## Outputs / Deliverables
- `ops/agent_root_domain_summary.py`
- `prompts/root-domain-summary.md`
- `domain/domain.md`.
- Tests with a stubbed agent.

## Implementation notes
- Language: **Python**.

## Acceptance criteria
- [ ] `domain/domain.md` is produced with valid frontmatter.
- [ ] All §10.4.4 sections are present in the body.
- [ ] Re-running with no changes is a no-op.

## Verification commands
```bash
python -m pytest -q tests/test_agent_root_domain_summary.py
python -m ops.validate_artifacts validate frontmatter domain/domain.md
```

## Open questions
- None significant.
