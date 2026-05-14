# Delta — taxonomy

## MODIFIED

### Sampling unit

Taxonomy discovery samples **projection outputs**, not evidence records. A `NormalizedDoc` for sampling purposes is the same as before, but the underlying scope is broader: an RFP that splits into 5 sections offers 5 sample candidates (plus the whole-document if that projection is also enabled), instead of 1.

This generally improves discovery coverage on cross-functional sources.

### Frontmatter awareness

Discovery findings record the **projection** that produced the sampled doc. The `TaxonomyFinding` schema gains:

```json
{
  "iteration": 3,
  "source_type": "rfp",
  "source_id": "doc-12",
  "projection": "rfp:section_split",
  "projection_output": "03-payments-integration.md",
  ...
}
```

This makes it easier to see in the proposal whether a missing/ambiguous value clusters around specific projection types.

### Sampling diversity

Diversity axes used in stratified sampling now include `projection` as an axis when the source type has more than one projection enabled. This ensures discovery sees outputs from each projection rather than over-sampling whichever projection produced more docs.

## REMOVED

- Nothing structural.

## ADDED

Nothing new; this is purely about pointing the discovery loop at the projections tree and recording projection provenance in findings.

## Related

- [Change folder 001](../../changes/001-projection-primitive/proposal.md).
