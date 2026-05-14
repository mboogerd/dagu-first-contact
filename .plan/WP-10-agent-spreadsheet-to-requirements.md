# WP-10: Spreadsheet → requirements (agent-generated converter)

## Context
Implements the *agent* half of spec §8.4.1. An agent inspects each imported spreadsheet and produces a converter script under `generated/spreadsheet-converters/`. The runner from WP-09 (executed downstream after human approval) actually generates the normalized markdown.

Prerequisite WPs: WP-09.

## Scope
### In scope
- A driver `ops/agent_generate_spreadsheet_converters.py` (or similar) that:
  - Iterates over `import/spreadsheet/<name>.<ext>` for which `generated/spreadsheet-converters/<name>.py` is missing OR its source hash has changed since the converter was generated.
  - For each, gathers a structural fingerprint of the workbook (sheet names, header rows, sample of first ~20 rows per sheet, inferred types) using deterministic Python code.
  - Calls an *agent* with a prompt template (committed under `prompts/spreadsheet-converter.md`) that includes:
    - the spreadsheet fingerprint,
    - the converter contract (importing/repeating WP-09's contract),
    - example output schema (the `normalized/requirements/<name>.md` shape from spec §8.4.1).
  - Writes the agent's response to `generated/spreadsheet-converters/<name>.py`.
  - Writes a sidecar `generated/spreadsheet-converters/<name>.agent.yaml` recording: agent identifier, prompt hash, input fingerprint hash, generated_at.
  - Does **not** auto-approve. Approval is a separate human step (WP-26).
- The agent *integration* is left open. At pickup, evaluate:
  - Dagu's native LLM/agent step support
  - CLI tools: `opencode`, `claude` (Claude Code), `codex`
  - Agent Context Protocol servers
  - Direct API call to a chosen provider
  Choose one, document the choice in `prompts/spreadsheet-converter.md`'s header, and isolate it behind a single function `call_agent(prompt: str, *, system: str | None = None) -> str` in `ops/_agent.py` so it can be swapped.

### Out of scope
- Executing converters (WP-09).
- The approval gate (WP-26).
- Any agent integration beyond what this WP needs (other WPs reuse `ops/_agent.py`).

## Inputs
- `import/spreadsheet/*`.
- `prompts/spreadsheet-converter.md` (the prompt template; committed).

## Outputs / Deliverables
- `ops/agent_generate_spreadsheet_converters.py`
- `ops/_agent.py` (shared agent-call abstraction; first WP to introduce it).
- `prompts/spreadsheet-converter.md`.
- `generated/spreadsheet-converters/<name>.py` (generated at runtime, not committed unless the user chooses to).
- `generated/spreadsheet-converters/<name>.agent.yaml` sidecar.
- Tests `tests/test_agent_generate_spreadsheet_converters.py` using a stubbed `call_agent` (no real LLM in CI).

## Implementation notes
- Language: **Python**.
- The fingerprint step uses `openpyxl` (xlsx) or `pandas` (xlsx/ods/csv). Keep dependencies modest.
- Prompt template must be explicit about safety: no network calls in the converter, only stdlib + project deps, no `eval`/`exec`.
- The agent output must be valid Python. Strip Markdown code fences if the chosen agent wraps in them; reject anything other than a single Python module.
- Record the *exact* prompt sent (template + filled values) hashed into the sidecar, so we can detect prompt drift.

## Acceptance criteria
- [ ] With `call_agent` stubbed to return a known-good converter, the driver produces both the `.py` and `.agent.yaml` files.
- [ ] Re-running with no changes is a no-op (hash-skipped).
- [ ] Changing the spreadsheet causes regeneration (and clears any previous approval in `.approved.yaml`).
- [ ] The driver never writes to `.approved.yaml`.
- [ ] The driver refuses to overwrite a converter that has a current approval, unless `--force` is passed (and `--force` clears the approval).
- [ ] (human review) Prompt template is committed and reviewable.

## Verification commands
```bash
python -m pytest -q tests/test_agent_generate_spreadsheet_converters.py
# Real run requires picking + configuring an agent integration first.
```

## Open questions
- Should the agent see *any actual cell values* beyond the fingerprint (privacy)? Default: yes, the fingerprint is sample-based; document this in the prompt and README.
- Cost/latency: caching `call_agent` results by prompt hash is desirable. Decide whether `_agent.py` does that or each driver does. Recommendation: `_agent.py` has an optional disk cache under `.state/agent-cache/`.
