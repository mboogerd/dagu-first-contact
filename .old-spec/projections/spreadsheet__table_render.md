# Projection: `spreadsheet:table_render`

**Kind.** Deterministic.
**Default intent.** `implemented`
**Default status.** `implemented`

## Purpose

Flatten a spreadsheet into a markdown document with tables. Each sheet becomes a section; each table is rendered as a markdown table.

## Inputs

- `evidence/spreadsheet/<id>/` — the source spreadsheet (XLSX, CSV, or Google Sheets export).

## Parameters

None. `parameters_schema: null`.

## Output contract

**Single output file:** `projections/spreadsheet/<id>/table_render/<id>.md`

The markdown body contains one `## <sheet-name>` section per sheet, with the sheet's content rendered as a markdown table. Empty sheets are omitted. Merged cells are expanded.

## Cache key

```
hash(projection_name, projection_version, evidence_content_hash)
```

## Failure modes

- **Rich formatting loss.** Conditional formatting, cell colors, and formulas are not preserved. Mitigation: original stays in `evidence/`.
- **Very wide tables.** Spreadsheets with many columns produce markdown tables that are hard to read. Acceptable: the content is still extractable even if not pretty.
