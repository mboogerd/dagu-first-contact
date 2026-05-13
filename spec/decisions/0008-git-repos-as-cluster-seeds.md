# [D-8] Git repos as cluster seeds

**Status.** Accepted.

**Decision.** Initial clusters are seeded from git repos. Other docs assigned to the nearest repo cluster.

**Rationale.** Repos are a strong prior — they reflect team and system boundaries. Better starting point than asking an LLM to invent a taxonomy.

**Alternatives considered.**
- Pure unsupervised clustering on embeddings — rejected: less stable, less explainable.

**Trade-offs accepted.** Bias toward existing repo structure. If the repo structure is wrong (monolith, or wrong split), clusters inherit that. Acceptable: an assessment that mirrors current structure is useful even if structure is suboptimal. For larger services / monoliths, a projection-style approach is anticipated (see [open-questions.md](../open-questions.md)).

**Related.** [cluster-structural spec](../specs/cluster-structural/spec.md); [D-22](0022-git-repo-curated-summary.md).
