# [D-50] Source-declared intent

**Status.** Accepted.

**Decision.** Each projection declares an `intent` (`implemented | planned | proposed | mixed`) and a `default_status` in its output frontmatter. Requirements extracted from the projection inherit the default status unless the extractor has strong contrary evidence. The consolidate stage's `status_disagreement` conflict detection suppresses false positives when the difference between two sources' statuses is explained by their projections' differing intents.

Suppression rule: `status_disagreement` is suppressed when the set of source `intent` values is `{implemented, planned}` or `{implemented, proposed}` or `{planned, proposed}` and the resolved statuses align with those intents.

**Rationale.** "This evidence describes intended state, not built state" is a property of the evidence/projection, not of each requirement within it. Without intent declaration, ingesting a client's estimation report (planned work) alongside implemented code would produce false `status_disagreement` conflicts on every matching requirement. The suppression rule is the primary defense against this class of false positives.

**Alternatives considered.**
- Infer intent purely from `source_type` — too coarse; a Jira project has mixed intent.
- Suppress all status disagreements — hides genuine conflicts.
- Per-requirement intent declaration — too verbose; the projection level is the right granularity.

**Trade-offs accepted.** `intent: mixed` (used by Jira) requires the extractor to infer status per requirement from source-specific cues, which is the status quo. The complexity is bounded to that one case.

**Related.** [ingest spec](../specs/ingest/spec.md); [consolidate spec](../specs/consolidate/spec.md); [D-49](0049-projection-primitive.md); change folder [001-projection-primitive](../changes/001-projection-primitive/proposal.md) (origin).
