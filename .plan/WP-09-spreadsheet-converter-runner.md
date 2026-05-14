# WP-09: Spreadsheet converter contract & runner (`ops/run_spreadsheet_converters.py`)

## Context
Implements the deterministic half of spec §8.4.1. A converter script per spreadsheet lives under `generated/spreadsheet-converters/` (produced in WP-10 by an agent and approved by a human in WP-26). This WP defines the *contract* those converters must follow and the *runner* that executes them.

Prerequisite WPs: WP-02, WP-05.

## Scope
### In scope
- Define the converter contract. Each generated converter is a Python module `generated/spreadsheet-converters/<spreadsheet-name>.py` with a single function:
  ```python
  def convert(input_path: Path, output_dir: Path) -> Path:
      """Produce normalized/requirements/<spreadsheet-name>.md and return its path."""
  ```
  The runner is responsible for filling frontmatter; the converter only writes the markdown body and may pass extra frontmatter via return metadata. Define the exact return contract — either:
  - return the output path and side-effect frontmatter via `output_dir / "<name>.frontmatter.yaml"`, or
  - return `tuple[Path, dict]` where the dict is extra frontmatter.
  Pick one at pickup and document.
- CLI: `python -m ops.run_spreadsheet_converters [--only NAME ...]`.
- Discovery: every `import/spreadsheet/<name>.<ext>` with a matching `generated/spreadsheet-converters/<name>.py` is run. Spreadsheets without a converter are listed in the output as "skipped — no approved converter" with a non-zero exit code at the end.
- Sandboxing: the runner refuses to execute a converter whose SHA-256 does not match the value recorded in `generated/spreadsheet-converters/.approved.yaml` (this is the "approved by human" gate from WP-26). The file format:
  ```yaml
  converters:
    legacy-requirements:
      sha256: <sha256-of-legacy-requirements.py>
      approved_at: 2026-05-14T12:00:00Z
      approved_by: merlijn
  ```
- After execution, the runner writes the normalized markdown via `ops/_artifact.write_artifact` with frontmatter:
  ```yaml
  artifact_type: requirements-normalized
  generated_by: 10-normalize
  generated_at: ...
  inputs: [import/spreadsheet/<name>.xlsx]
  input_hashes: { ... }
  source_type: spreadsheet
  source_file: import/spreadsheet/<name>.xlsx
  ```
- Idempotent: if input hash and converter hash both match the previous run, skip.

### Out of scope
- Generating converters (WP-10).
- The Dagu-side approval step (WP-26).

## Inputs
- `import/spreadsheet/*`.
- `generated/spreadsheet-converters/*.py`.
- `generated/spreadsheet-converters/.approved.yaml`.

## Outputs / Deliverables
- `ops/run_spreadsheet_converters.py`
- `schemas/approved-converters.schema.json` + validator plug-in.
- A documented converter contract (`generated/spreadsheet-converters/README.md`) including the function signature, allowed dependencies (must work with the project's `pyproject.toml`), and the I/O guarantees.
- `tests/test_run_spreadsheet_converters.py` with a tiny hand-written converter as a fixture.

## Implementation notes
- Language: **Python**. Use `importlib.util.spec_from_file_location` to load the converter module.
- Run each converter in a subprocess (so a single bad converter cannot crash the runner). Pass `--input` and `--output-dir` arguments; the wrapper inside the runner ensures the converter is invoked as a module function (a small `__main__` shim can be appended at import time, or the runner can call the function directly in-process after deciding subprocess isolation isn't required — pick at pickup).
- Treat any converter that imports outside the project's pinned deps as a hard failure (use a pre-scan or rely on import errors).

## Acceptance criteria
- [ ] A test fixture converter produces `normalized/requirements/<name>.md` whose frontmatter validates.
- [ ] Tampering with the converter (changing its bytes) makes the runner refuse to execute it unless `.approved.yaml` is updated.
- [ ] A spreadsheet without an approved converter results in a clear "skipped" message and non-zero exit.
- [ ] Re-running with no changes is a no-op (verify via mtimes/hashes).
- [ ] `python -m ops.validate_artifacts validate all` passes on the resulting state.

## Verification commands
```bash
python -m ops.run_spreadsheet_converters
python -m pytest -q tests/test_run_spreadsheet_converters.py
```

## Open questions
- Subprocess isolation vs in-process: trade-off between safety and convenience. Recommend in-process for MVP given the human approval gate; reconsider if converters grow.
- Should `.approved.yaml` be checked into git? Yes — it records human decisions.
