# Projection: `transcript:speaker_grouped`

**Kind.** Deterministic.
**Default intent.** `proposed`
**Default status.** `proposed`

## Purpose

Render a transcript with speaker turn boundaries preserved. Each speaker turn is a block, making it easy for extractors to attribute statements to speakers.

## Inputs

- `evidence/transcript/<id>/` — the source transcript (text, SRT, VTT, or structured JSON).

## Parameters

None. `parameters_schema: null`.

## Output contract

**Single output file:** `projections/transcript/<id>/speaker_grouped/<id>.md`

The markdown body contains sequential speaker turns:

```markdown
### Speaker A (00:01:23)

Statement text...

### Speaker B (00:02:45)

Response text...
```

Timestamps are included when available. Unknown speakers are labeled `Unknown Speaker N`.

## Cache key

```
hash(projection_name, projection_version, evidence_content_hash)
```

## Failure modes

- **Speaker identification errors.** Source transcripts may have incorrect speaker labels. Mitigation: the projection preserves whatever the source provides; corrections happen at the evidence level.
- **Overlapping speech.** Transcripts with overlapping speakers may lose attribution clarity. Acceptable for extraction purposes.
