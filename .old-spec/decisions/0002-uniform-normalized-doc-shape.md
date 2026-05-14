# [D-2] Uniform normalized-doc shape

**Status.** Accepted.

**Decision.** All ingested artifacts become `{markdown + YAML frontmatter}` with a fixed frontmatter schema.

**Rationale.** Lets every downstream stage be source-agnostic. Adding a new source type doesn't ripple.

**Alternatives considered.**
- Per-source-type schemas through the pipeline.

**Trade-offs accepted.** Some source-specific information lives in the `extra:` frontmatter field; extractors can use it but shouldn't require it.

**Related.** Principle 4 in [principles.md](../principles.md); [ingest spec](../specs/ingest/spec.md).
