# Projection: `rfp:section_split`

**Kind.** Deterministic.
**Default intent.** `proposed`
**Default status.** `proposed`

## Purpose

Split an RFP into one markdown file per top-level section. Each section lands as an independent projection output that can be assigned to a different domain. This is the multi-output proof case: a single evidence record producing multiple downstream-ready documents.

## Inputs

- `evidence/rfp/<doc-id>/` — the source RFP (PDF, DOCX, or markdown).

## Parameters

```yaml
parameters_schema:
  type: object
  properties:
    min_section_length:
      type: integer
      default: 200
      description: Minimum character count for a section to be emitted as its own file. Shorter sections are merged with the next section.
```

## Output contract

**Multiple output files:** `projections/rfp/<doc-id>/section_split/<NN>-<section-slug>.md`

Files are numbered sequentially (`01-`, `02-`, ...) to preserve document order. The section slug is derived from the section heading (lowercased, hyphenated). Each file contains one section's content with the section heading as the top-level `#` header.

Sections shorter than `min_section_length` are merged with the subsequent section.

## Cache key

```
hash(projection_name, projection_version, serialized(projection_params), evidence_content_hash)
```

## Failure modes

- **Section detection failures.** Documents without clear section headers may produce a single large file or many tiny fragments. Mitigation: the `min_section_length` parameter controls the minimum granularity.
- **Cross-section context loss.** A section may reference concepts defined in an earlier section. Each section file is self-contained for extraction purposes; cross-references are the extractor's problem (it sees each file independently).
