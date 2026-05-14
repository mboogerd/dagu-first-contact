# WP-08: Jira JSON → markdown normalizer (`ops/jira_json_to_markdown.py`)

## Context
Implements spec §8.4.3. Deterministic conversion of raw Jira payloads into normalized markdown with frontmatter. The spec is explicit: **no agent for this**.

Prerequisite WPs: WP-02, WP-07.

## Scope
### In scope
- CLI: `python -m ops.jira_json_to_markdown [--only PROJECT ...] [--input import/jira] [--output normalized/jira]`.
- For each `import/jira/[PROJECT]/issue-payloads/*.json`:
  - Produce `normalized/jira/[PROJECT]/<ISSUE-KEY>.md`.
  - Frontmatter exactly matches spec §8.4.3 example:
    ```yaml
    artifact_type: jira-normalized
    generated_by: 10-normalize
    generated_at: 2026-05-14T12:00:00Z
    inputs:
      - import/jira/BILLING/issue-payloads/BILLING-123.json
    input_hashes:
      import/jira/BILLING/issue-payloads/BILLING-123.json: <sha256>
    source_type: jira
    project: BILLING
    issue_key: BILLING-123
    status: In Progress
    issue_type: Story
    assignee: Jane Doe
    labels: [payments, migration]
    updated: 2026-05-10T09:30:00Z
    ```
  - Body sections (always emitted, possibly empty):
    - `# <ISSUE-KEY>: <summary>`
    - `## Description`
    - `## Comments` (each comment as a level-3 heading with author + timestamp)
    - `## Links` (issue links if present)
  - Convert Atlassian Document Format (ADF) descriptions/comments to markdown. A complete ADF→md is large; produce a pragmatic subset (paragraphs, text, mentions, links, ordered/unordered lists, code blocks, headings) and emit `<!-- adf-unhandled: <node-type> -->` markers for everything else.
- Idempotent and content-addressed: skip files whose `input_hashes` matches the existing output's frontmatter.
- Output must validate against `schemas/frontmatter.schema.json`.

### Out of scope
- Agent interpretation; this is deterministic only.
- Cross-issue link resolution beyond emitting the raw key.

## Inputs
- `import/jira/[PROJECT]/issue-payloads/*.json`.

## Outputs / Deliverables
- `ops/jira_json_to_markdown.py`
- An ADF→markdown helper module (`ops/_adf.py` or similar) with its own unit tests.
- `tests/test_jira_json_to_markdown.py` with at least 3 fixture payloads (simple text, ADF with lists/code, ADF with unsupported nodes).
- README snippet.

## Implementation notes
- Language: **Python**, standard library + `pyyaml`. No need for a Jira SDK (input is already JSON on disk).
- Reuse `ops/_artifact.write_artifact` from WP-02.
- Keep the ADF converter pure (no I/O) so it is trivially testable.

## Acceptance criteria
- [ ] Given fixture payloads, the normalizer produces exactly the expected `.md` files (compare against committed expected outputs).
- [ ] Unsupported ADF nodes appear as comment markers but never break the run.
- [ ] Re-running with no input changes leaves files untouched (mtime stable).
- [ ] `python -m ops.validate_artifacts validate frontmatter normalized/jira/**/*.md` exits 0.
- [ ] `python -m pytest tests/test_jira_json_to_markdown.py` passes.

## Verification commands
```bash
python -m ops.jira_json_to_markdown
python -m ops.validate_artifacts validate frontmatter "normalized/jira/**/*.md"
python -m pytest -q tests/test_jira_json_to_markdown.py
```

## Open questions
- Should `## Links` resolve issue keys to relative paths if the target was imported? Default: emit the key only; cross-linking is a later concern.
