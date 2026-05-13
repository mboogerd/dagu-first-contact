# [D-9] Hash-keyed summary cache

**Status.** Accepted.

**Decision.** Cluster summary cache key is `hash(sorted(member_content_hashes) + prompt_version + model)`.

**Rationale.** Recursive summarization with hash-keyed cache keeps cost bounded: unchanged subtrees cost nothing on re-runs.

**Alternatives considered.**
- Re-summarize on every run (expensive).
- Time-based cache (incorrect).

**Trade-offs accepted.** Cache key recomputation is itself work; negligible at this scale.

**Related.** [cluster-semantic spec](../specs/cluster-semantic/spec.md).
