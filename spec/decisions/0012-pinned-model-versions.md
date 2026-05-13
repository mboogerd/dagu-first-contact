# [D-12] Pinned model versions

**Status.** Accepted.

**Decision.** `config/models.yaml` pins exact model IDs (e.g., `claude-sonnet-4-5-20250929`). No `*-latest` aliases.

**Rationale.** Reproducibility. A model update mid-assessment otherwise invalidates the cache silently and changes outputs.

**Alternatives considered.**
- Latest models — faster to benefit from improvements; not reproducible.

**Trade-offs accepted.** Manual model upgrades required.

**Related.** [orchestration spec](../specs/orchestration/spec.md).
