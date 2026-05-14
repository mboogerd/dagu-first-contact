# [D-8] Git repos as domain seeds

**Status.** Accepted.

**Decision.** Initial domains are seeded from git repos. Other docs assigned to the nearest repo domain.

**Rationale.** Repos are a strong prior — they reflect team and system boundaries. Better starting point than asking an LLM to invent a taxonomy.

**Alternatives considered.**
- Pure unsupervised clustering on embeddings — rejected: less stable, less explainable.

**Trade-offs accepted.** Bias toward existing repo structure. If the repo structure is wrong (monolith, or wrong split), domains inherit that. Acceptable: an assessment that mirrors current structure is useful even if structure is suboptimal. For larger services / monoliths, a projection-style approach is available (see [D-49](0049-projection-primitive.md), [open-questions.md](../open-questions.md)).

**Related.** [domain-structural spec](../specs/domain-structural/spec.md); [D-49](0049-projection-primitive.md).
