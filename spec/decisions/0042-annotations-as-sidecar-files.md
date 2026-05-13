# [D-42] Cross-cluster findings are sidecar annotations; per-cluster records remain immutable

**Status.** Accepted.

**Decision.** The cross-cluster stage does NOT modify `clusters/<cluster>/consolidated/requirements.json`. Instead, it writes `clusters/<cluster>/consolidated/cross_cluster_annotations.json` as a sidecar referencing the per-cluster `ConsolidatedRequirement` records that participate in cross-cluster conflicts. Downstream consumers (review queue, report) read both files together.

**Rationale.** Principle 2 — immutability of upstream layer outputs — is a core invariant. Allowing the cross-cluster stage to mutate per-cluster outputs would break that invariant. Sidecar annotations preserve immutability, keep the bidirectional reference intact, and make re-runs idempotent.

**Alternatives considered.**
- Mutate per-cluster `requirements.json` directly — breaks immutability principle.
- Push references only in one direction — makes "what conflicts does this requirement participate in?" a search rather than a lookup.

**Trade-offs accepted.** Two files instead of one. Mitigation: review queue generation merges them.

**Related.** [cross-cluster spec](../specs/cross-cluster/spec.md); Principle 2.
