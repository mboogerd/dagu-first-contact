# [D-4] Source-agnostic extractors

**Status.** Accepted.

**Decision.** One prompt per extraction type, regardless of source. `source_type` is context, not control flow.

**Rationale.** Prevents prompt drift across source-specific extractors.

**Alternatives considered.**
- Per-source extractors (`extractRequirementsFromGit`, etc., as in the original draft).

**Trade-offs accepted.** A single prompt must handle the variance across sources. Mitigated by including `source_type` and a short style-guide-per-source in the prompt template.

**Related.** [extract spec](../specs/extract/spec.md); [D-16](0016-three-explicit-extractors.md).
