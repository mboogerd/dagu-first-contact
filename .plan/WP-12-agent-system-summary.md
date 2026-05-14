# WP-12: System summary (agent)

## Context
Implements spec §9.4.1. For each imported git repository produces a markdown summary at `domain/systems/<repo-name>.md`. This is the first "domain projection" step.

Prerequisite WPs: WP-02, WP-04, WP-10 (only for `ops/_agent.py`).

## Scope
### In scope
- Driver `ops/agent_system_summary.py`:
  - For each `import/git/<name>/` that lacks an up-to-date `domain/systems/<name>.md`:
    - Build a deterministic repository fingerprint:
      - top-level file list
      - languages detected (extension counts)
      - presence/contents of `README*`, `CODEOWNERS`, `package.json` / `pom.xml` / `build.gradle*` / `pyproject.toml`, `Dockerfile`, `docker-compose*.yml`, deployment manifests
      - Git history summary (top contributors, recent commit messages — capped)
      - Module/folder tree to a configurable depth
    - Optionally include a "salient files" excerpt: heads of detected interface files (controllers, API definitions, OpenAPI specs).
    - Write the fingerprint to `.state/system-fingerprint/<name>.json` for traceability.
    - Call the agent (via `ops/_agent.py`) with the prompt at `prompts/system-summary.md`. The prompt enforces the structure in spec §9.4.1:
      `Purpose, Responsibilities, Owned data, External dependencies, Internal modules, Public APIs/events/interfaces, Runtime/deployment, Technology stack, Known consumers/providers, Ownership hints, Evidence, Confidence`.
    - Write `domain/systems/<name>.md` via `write_artifact` with the frontmatter from spec §9.4.1:
      ```yaml
      artifact_type: system-summary
      generated_by: 20-domain-analysis
      generated_at: ...
      inputs: [import/git/<name>]
      input_hashes: { import/git/<name>: <dir-hash> }
      system: <name>
      source_repo: import/git/<name>
      commit: <commit hash from import manifest>
      confidence: low|medium|high
      ```
- Idempotent: skip when input hash + prompt hash unchanged.
- Reads the commit from `import/git/<name>/.import-manifest.yaml`.

### Out of scope
- Cross-system interactions (WP-13).
- Boundary proposals (WP-14).

## Inputs
- `import/git/*` and their import manifests.
- (Optional) `normalized/jira/*` for ticket-based ownership hints; if absent, skip those hints rather than fail.
- `prompts/system-summary.md`.

## Outputs / Deliverables
- `ops/agent_system_summary.py`
- `prompts/system-summary.md`
- `.state/system-fingerprint/<name>.json`
- Tests with a stubbed agent.

## Implementation notes
- Language: **Python**.
- The fingerprint must be small enough to fit comfortably in a single agent context. If a repo is large, fall back to a layered approach: top-level summary → per-module pass → consolidation. Define the threshold (e.g. >200 source files) in the prompt template.
- Use `pygments`/extension maps for language detection; avoid running language-specific parsers in MVP.

## Acceptance criteria
- [ ] For a test fixture repo, the driver produces a `domain/systems/<name>.md` that validates against the frontmatter schema.
- [ ] The system summary body contains every required section heading from §9.4.1.
- [ ] Re-running with no changes is a no-op.
- [ ] When the repo lacks a CODEOWNERS file, ownership hints section explicitly states "no CODEOWNERS file present" rather than fabricating.
- [ ] (human review) Prompt is committed; output for a fixture repo is sensible.

## Verification commands
```bash
python -m pytest -q tests/test_agent_system_summary.py
python -m ops.validate_artifacts validate frontmatter "domain/systems/*.md"
```

## Open questions
- For huge repos, do we cap fingerprint size or do multi-pass? Default: cap + warning; multi-pass only if cap is hit frequently.
