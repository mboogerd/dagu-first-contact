# WP-32: MVP fixtures & end-to-end smoke run

## Context
Implements spec §18.1 (First MVP). Provides a self-contained dataset and runbook to exercise the full pipeline end-to-end.

Prerequisite WPs: WP-31.

## Scope
### In scope
- A `tests/fixtures/` (and optionally `mvp/`) tree containing:
  - 3 small git repositories — either checked-in bare repos under `tests/fixtures/repos/` or a script that generates them. Each repo has enough structure (README, a couple of source files, CODEOWNERS, a Dockerfile or deployment manifest) to be meaningfully summarised.
  - 1 small spreadsheet under `sources/spreadsheets/`.
  - 1 small RFP PDF under `sources/rfp/` (a few pages, generated from markdown via `pandoc` or similar in a setup script).
  - 1 Jira project's worth of payloads (committed JSON) under `tests/fixtures/jira/`. A flag on the importer (`--from-fixtures PATH`) reads from local files instead of calling the API.
- A `tests/fixtures/references-mvp.yaml` pointing at the above.
- A runbook `MVP.md` at the repo root with the exact commands to:
  1. install deps
  2. configure the chosen agent integration
  3. run `dagu start dagu/main.yaml --params="references=tests/fixtures/references-mvp.yaml"`
  4. expected approval prompts and how to satisfy them
  5. expected final outputs
- A non-LLM "dry mode": every `ops/_agent.py` call can be backed by a fixture-replay implementation so the full pipeline runs deterministically in CI. Provide pre-recorded agent responses for the MVP fixtures.
- A CI workflow (GitHub Actions or equivalent) that runs the dry-mode end-to-end pipeline and asserts the final report exists and validates.

### Out of scope
- Larger datasets (spec §18.2 second iteration).
- Real LLM calls in CI.

## Inputs
- All previous WPs.

## Outputs / Deliverables
- `tests/fixtures/...` populated as above.
- `MVP.md`.
- CI workflow file.
- Fixture-replay support inside `ops/_agent.py` (a `OPS_AGENT_BACKEND=fixture` mode that reads pre-recorded responses keyed by prompt hash from `tests/fixtures/agent-responses/`).

## Implementation notes
- The fixture-replay agent backend is what makes this WP critical — without it, the pipeline cannot be CI-tested.
- Keep fixture sizes small (< 1 MB total for non-PDF; PDF can be a few hundred KB).
- The `--from-fixtures` flag on `ops/import_jira.py` may require adjusting WP-07; if so, scope that adjustment into this WP.

## Acceptance criteria
- [ ] `dagu start dagu/main.yaml --params="references=tests/fixtures/references-mvp.yaml" OPS_AGENT_BACKEND=fixture` runs end-to-end to completion without human input (approval steps auto-approve in fixture mode — document this).
- [ ] `output/final-report.md` exists and validates.
- [ ] CI workflow runs the pipeline in dry mode and passes on a fresh clone.
- [ ] `MVP.md` is sufficient for a new developer to produce the same outputs locally with a real agent.

## Verification commands
```bash
OPS_AGENT_BACKEND=fixture dagu start dagu/main.yaml --params="references=tests/fixtures/references-mvp.yaml"
test -f output/final-report.md
python -m ops.validate_artifacts validate all
```

## Open questions
- Auto-approval in fixture mode: implement via env var `OPS_APPROVAL_BACKEND=auto-approve` or via a sentinel file. Recommendation: env var, mirroring the agent backend pattern.
- Whether to commit the rendered RFP PDF or generate it in a setup script. Recommendation: generate via `setup-fixtures.sh` so the repo stays small.
