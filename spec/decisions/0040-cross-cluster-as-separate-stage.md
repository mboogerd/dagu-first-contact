# [D-40] Cross-cluster reconciliation is its own stage with a priority boost

**Status.** Accepted (trimmed for v1).

**Decision.** Cross-cluster reconciliation runs as a separate stage, after per-cluster consolidation. It takes all `ConsolidatedRequirement` records as input, produces `cross_cluster/conflicts.json` plus sidecar `cross_cluster_annotations.json` per affected cluster, and regenerates `review_queue.json` with a `cross_cluster_boost` (default 0.20) added to participating items' `review_priority`.

**Rationale.** Conflicts between sibling clusters are missed by bottom-up consolidation; a separate stage is the cleanest place to put logic that requires global-scope inputs. The priority boost is the mechanism by which cross-cluster findings reach the consultant.

**Alternatives considered.**
- Inline in consolidate as a recursive root pass — couples within-cluster and cross-cluster logic.
- A separate command rather than always running as part of `consolidate` — silent skipping is worse than always running with the option to disable via config.
- No priority boost; just publish findings in a separate artifact — cross-cluster findings have higher review value and should be prioritized accordingly.

**Trade-offs accepted.** Extra phase to maintain; additional cost. The boost magnitude (0.20) is a guess in v1 — calibration is deferred. Acceptable: cost is bounded by `max_candidate_pairs`; cache reuse on stable inputs makes re-runs cheap.

**Related.** [cross-cluster spec](../specs/cross-cluster/spec.md); [R-23](../risks.md).
