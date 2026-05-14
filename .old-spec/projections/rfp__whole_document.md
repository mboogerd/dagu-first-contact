# Projection: `rfp:whole_document`

**Kind.** Deterministic.
**Default intent.** `proposed`
**Default status.** `proposed`

## Purpose

Render the entire RFP as a single markdown document. This is the default projection for RFPs; it preserves the document's structure as-is for extraction and domain assignment.

## Inputs

- `evidence/rfp/<doc-id>/` — the source RFP (PDF, DOCX, or markdown).

## Parameters

None. `parameters_schema: null`.

## Output contract

**Single output file:** `projections/rfp/<doc-id>/whole_document/<doc-id>.md`

The markdown body is a faithful rendering of the RFP content with section headers preserved. Tables are rendered as markdown tables where feasible; embedded images are referenced but not inlined.

## Cache key

```
hash(projection_name, projection_version, evidence_content_hash)
```

## Failure modes

- **Complex formatting loss.** RFPs with rich formatting, embedded tables, or images may lose information during markdown conversion. Mitigation: original stays in `evidence/`; normalization warnings are surfaced.
- **Very large documents.** RFPs exceeding context windows in downstream stages. Mitigation: `rfp:section_split` projection is available as an alternative.
