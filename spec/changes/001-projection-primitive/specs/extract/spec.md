# Delta — extract

## MODIFIED

### Input location

Extractors now read from `projections/<source>/<id>/<projection>/<file>.md` instead of `normalized/<source>/<id>.md`. The file shape is unchanged (markdown + frontmatter); only the path differs.

Each projection output is treated as an independent input. A single piece of evidence with multiple projections produces multiple extraction runs (one per projection output).

### Cache key

The extraction cache key gains the projection identity:

```
hash(
  prompt_text,
  doc_content_hash,
  model_id,
  schema,
  locked_taxonomy_version,
  projection_name,
  projection_version
)
```

Projection version is added so that contract/prompt changes to a projection trigger re-extraction of its outputs (even if `content_hash` happens to be identical).

### Raw-evidence access

[D-23](../../decisions/0023-raw-evidence-accessible-to-extractors.md) is unchanged: extractors MAY consult `evidence/<source_type>/<source_id>/` when the projection signals it (e.g., `git:repo_summary` carries enough information that the extractor may want to dig into the underlying code).

The mechanism: each projection contract declares whether `evidence/` access is expected. Extractors check the projection's contract before reading evidence. This was implicit in v0 (git was special); v1 makes it explicit per projection.

### Status inference and intent

`extract_requirements` now honors the `intent` and `default_status` frontmatter fields:

- When `intent` is `implemented | planned | proposed`, the extractor's default for each requirement's `status` is the projection's `default_status`.
- When `intent` is `mixed`, the extractor infers status per requirement as before (using source_type cues and source-specific metadata in `extra:`).
- When the extractor has **strong contrary evidence**, it MAY override the default and emit a different status. The override is recorded with the requirement.

## REMOVED

- The phrasing "extractors MAY consult the underlying `evidence/<source_type>/<source_id>/` when `normalization_kind: curated_summary`" — replaced by the per-projection contract mechanism above.

## ADDED

### Failure modes (new)

- **Per-projection status mis-classification across same evidence.** A single piece of evidence with multiple projections may produce conflicting status values across projections of the same evidence. By design: each projection has its own intent; if two projections of the same evidence have different intents, the resulting requirements legitimately differ on status. This is **not** a `status_disagreement` (the suppression rule in consolidate handles it).

## Related

- [Change folder 001](../../changes/001-projection-primitive/proposal.md).
