# Work Package Index

This folder breaks `SPECIFICATION.md` into work packages (WPs) sized so a single agentic LLM pass can implement and verify each.

## Conventions for every WP

- **Source of truth**: `SPECIFICATION.md` at the repo root. If a WP and the spec disagree, the spec wins; raise the discrepancy in the WP's "Open questions" section before changing behaviour.
- **Language**: each WP decides its own implementation language and records the rationale in its "Implementation notes" section. Default expectation is Python for `ops/*.py` (the spec names them explicitly), but a WP may justify shell, Go, etc.
- **Agent steps**: WPs that require interpretive synthesis leave the *integration* open. At pickup time, evaluate at minimum:
  - Dagu's native LLM/agent step (if available in the installed Dagu version)
  - CLI tools available locally (`opencode`, `claude`, `codex`)
  - Agent Context Protocol (ACP) servers (claude code, codex)
  - A plain HTTP call to a chosen provider
  Pick one, document the choice in the WP, and make the script's invocation interface stable so the integration can be swapped later without changing callers.
- **Determinism boundary**: scripts under `ops/` MUST be deterministic. Anything requiring judgement belongs in an agent step.
- **Artifacts are the contract**: every step's output is files on disk. Tests verify files, not in-memory state.
- **Frontmatter**: every generated markdown artifact uses the frontmatter convention defined in WP-02.
- **No destructive moves** without an approval gate (per spec §3.5, §10.4.2, §19).
- **Acceptance criteria** in each WP are written so they can be executed/verified mechanically (file exists, JSON Schema validates, exit code, etc.). If a criterion needs human judgement, it is marked `(human review)`.

## Ordering

WPs are numbered in a recommended execution order. Dependencies are listed explicitly in each WP; some WPs can be parallelised.

## Index

| # | Title | Depends on | Optional |
|---|---|---|---|
| WP-01 | Project skeleton & conventions | – | |
| WP-02 | Frontmatter & artifact-metadata helper | WP-01 | |
| WP-03 | Validation tool foundation (`ops/validate_artifacts.py`) | WP-01, WP-02 | |
| WP-04 | Git importer (`ops/import_git.py`) | WP-01, WP-03 | |
| WP-05 | Spreadsheet importer (`ops/import_spreadsheets.py`) | WP-01, WP-03 | |
| WP-06 | PDF importer (`ops/import_pdfs.py`) | WP-01, WP-03 | |
| WP-07 | Jira importer (`ops/import_jira.py`) | WP-01, WP-03 | |
| WP-08 | Jira JSON → markdown normalizer | WP-02, WP-07 | |
| WP-09 | Spreadsheet converter contract & runner | WP-02, WP-05 | |
| WP-10 | Spreadsheet → requirements (agent) | WP-09 | |
| WP-11 | RFP PDF → markdown (agent) | WP-02, WP-06 | |
| WP-12 | System summary (agent) | WP-02, WP-04 | |
| WP-13 | Interaction model (agent) | WP-12 | |
| WP-14 | Suggested domain boundaries (agent) + schema | WP-12, WP-13, WP-03 | |
| WP-15 | Materialize subdomain folders | WP-14 | |
| WP-16 | Subdomain summary (agent) | WP-15 | |
| WP-17 | Root domain summary (agent) | WP-16 | |
| WP-18 | Requirements extraction (agent) + schema | WP-08, WP-10, WP-11, WP-03 | |
| WP-19 | Requirements mapping (agent) + schema | WP-18, WP-17 | |
| WP-20 | Requirements status classification (agent) + schema | WP-19 | |
| WP-21 | Conflict detection (agent) + schema | WP-20 | |
| WP-22 | Conflict resolutions (agent) + schema | WP-21 | |
| WP-23 | Roadmap synthesis (agent) + schema | WP-20, WP-22 | |
| WP-24 | Final report (agent) | WP-17, WP-23 | |
| WP-25 | Dagu workflow `00-import.yaml` | WP-04..WP-07 | |
| WP-26 | Dagu workflow `10-normalize.yaml` (incl. converter approval) | WP-08, WP-09, WP-10, WP-11 | |
| WP-27 | Dagu workflow `20-domain-analysis.yaml` | WP-12, WP-13, WP-14 | |
| WP-28 | Dagu workflow `30-domain-boundaries.yaml` (incl. boundary approval) | WP-15, WP-16, WP-17 | |
| WP-29 | Dagu workflow `40-requirements-analysis.yaml` (incl. resolution approval) | WP-18..WP-23 | |
| WP-30 | Dagu workflow `90-final-report.yaml` (incl. publish approval) | WP-24 | |
| WP-31 | Dagu `main.yaml` orchestration | WP-25..WP-30 | |
| WP-32 | MVP fixtures & end-to-end smoke run | WP-31 | |
| WP-33 | Sidecar filesystem watcher | WP-31 | optional |

## Work package template

```markdown
# WP-NN: <Title>

## Context
<Why this exists, which spec sections it implements, prerequisite WPs.>

## Scope
### In scope
- ...
### Out of scope
- ...

## Inputs
- <files/folders consumed>

## Outputs / Deliverables
- <files/folders produced, including code paths>

## Implementation notes
- Language choice and rationale.
- Key decisions to make at pickup time (especially agent integration).

## Acceptance criteria
- [ ] Mechanical, file/exit-code based checks.
- [ ] (human review) items where relevant.

## Verification commands
```bash
# Commands a reviewer can run to verify the WP.
```

## Open questions
- ...
```
