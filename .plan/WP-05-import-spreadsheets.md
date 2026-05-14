# WP-05: Spreadsheet importer (`ops/import_spreadsheets.py`)

## Context
Implements spec §7.4.2. Copies local spreadsheet files and exports Google Sheets into `import/spreadsheet/` in open/stable formats; writes manifests.

Prerequisite WPs: WP-01, WP-03.

## Scope
### In scope
- CLI: `python -m ops.import_spreadsheets [--only NAME ...] [--references PATH]`.
- For each entry under `spreadsheets:`:
  - `type: file` → copy `path` into `import/spreadsheet/[name].<ext>` preserving extension; if the source is a proprietary format (e.g. `.xls`), additionally produce a `.ods` or `.xlsx` companion using `libreoffice --headless --convert-to` if available.
  - `type: google` → use the Google Sheets API to export to the configured `export` format (default `xlsx`); also produce `.ods` for archival.
  - Write `import/spreadsheet/[name].import-manifest.yaml` containing:
    ```yaml
    name: legacy-requirements
    type: file              # or google
    source: sources/spreadsheets/legacy-requirements.xlsx   # or URL
    files:
      - import/spreadsheet/legacy-requirements.xlsx
      - import/spreadsheet/legacy-requirements.ods
    imported_at: 2026-05-14T12:00:00Z
    content_hash:
      import/spreadsheet/legacy-requirements.xlsx: <sha256>
    ```
- Skip work when content hash matches the previous manifest (idempotent reruns).
- Respect `--dry-run`.
- If Google credentials are absent, skip Google entries with a clear log line and a non-zero exit code at the end.

### Out of scope
- Parsing the spreadsheet contents (that's WP-09/WP-10).
- Versioning multiple snapshots — overwrite on each import.

## Inputs
- `references.yaml` (spreadsheets section).
- `sources/spreadsheets/*` for `type: file`.
- Google credentials via `GOOGLE_APPLICATION_CREDENTIALS` for `type: google`.

## Outputs / Deliverables
- `ops/import_spreadsheets.py`
- Extension of `schemas/import-manifest.schema.json` (or a sibling schema) to cover spreadsheet manifests; validator plug-in.
- `tests/test_import_spreadsheets.py` covering local file copy + format conversion (mock LibreOffice with a fake CLI on PATH) and a mocked Google export.
- README snippet.

## Implementation notes
- Language: **Python**. Use `gspread` or `google-api-python-client` for Google; pick the simpler option and record the choice.
- Detect LibreOffice via `shutil.which("libreoffice")`; if missing, log and skip conversion (not a hard failure).
- Reuse manifest helpers from WP-04 where structure is identical.

## Acceptance criteria
- [ ] Importer copies a local `.xlsx` and writes a manifest with matching hash.
- [ ] Importer is idempotent: a second run with no source changes writes no new files (verify mtimes or hashes).
- [ ] With a mocked Google export, importer produces an `.xlsx` in `import/spreadsheet/`.
- [ ] Without Google credentials and at least one `type: google` entry: exit code non-zero, but `type: file` entries still complete.
- [ ] `python -m ops.validate_artifacts validate all` accepts produced manifests.

## Verification commands
```bash
python -m ops.import_spreadsheets --references tests/fixtures/references-local.yaml
python -m pytest -q tests/test_import_spreadsheets.py
```

## Open questions
- Should we keep the original file untouched in `sources/` and never copy, only reference it? Default: copy, so `import/` is fully self-contained.
- Do we need per-sheet exports? Default: no — the whole workbook is one artifact at this stage.
