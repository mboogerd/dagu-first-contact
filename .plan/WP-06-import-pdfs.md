# WP-06: PDF importer (`ops/import_pdfs.py`)

## Context
Implements spec §7.4.3. Copies RFP PDFs into `import/pdf/` with normalized filenames and a manifest.

Prerequisite WPs: WP-01, WP-03.

## Scope
### In scope
- CLI: `python -m ops.import_pdfs [--only NAME ...] [--references PATH]`.
- For each entry under `rfp:`:
  - Copy `path` to `import/pdf/[name].pdf` (lowercased, hyphenated `name`; reject names with whitespace or path separators).
  - Verify the file is a valid PDF (first bytes `%PDF`).
  - Write `import/pdf/[name].import-manifest.yaml`:
    ```yaml
    name: main-rfp
    source: sources/rfp/main-rfp.pdf
    file: import/pdf/main-rfp.pdf
    bytes: 1234567
    sha256: ...
    imported_at: 2026-05-14T12:00:00Z
    ```
- Idempotent: skip if `sha256` of source matches previous manifest.

### Out of scope
- PDF text extraction (WP-11).

## Inputs
- `references.yaml` (rfp section).
- `sources/rfp/*.pdf`.

## Outputs / Deliverables
- `ops/import_pdfs.py`
- Schema/validator additions if the manifest shape differs from WP-04/WP-05 (try to keep them aligned).
- `tests/test_import_pdfs.py`.

## Implementation notes
- Language: **Python**, standard library only is sufficient.
- A header check (`open(p, "rb").read(5) == b"%PDF-"`) is enough; no need for a PDF library here.

## Acceptance criteria
- [ ] A valid PDF in `sources/rfp/` produces a manifest and a copy under `import/pdf/`.
- [ ] A non-PDF file referenced in `references.yaml` fails with a clear error and does not produce a manifest.
- [ ] Re-running the importer with the same source file is a no-op.
- [ ] `python -m ops.validate_artifacts validate all` accepts produced manifests.

## Verification commands
```bash
python -m ops.import_pdfs --references tests/fixtures/references-local.yaml
python -m pytest -q tests/test_import_pdfs.py
```

## Open questions
- Do we want to keep the original filename alongside the normalized one? Default: no — manifest records the source path.
