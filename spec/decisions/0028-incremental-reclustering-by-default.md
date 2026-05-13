# [D-28] Incremental re-clustering by default; full re-cluster on demand

**Status.** Accepted.

**Decision.** Cluster assignments are stable across runs by default: new docs are assigned to existing clusters via the same nearest-seed + HDBSCAN logic, but existing assignments are not revisited. A `--full` flag forces a complete re-cluster from scratch. A full re-cluster is automatically triggered when `embedding.revision`, `similarity.assignment_threshold`, or HDBSCAN params change.

**Rationale.** Cluster identity stability matters during an iterative assessment. New evidence usually fits existing clusters; the cost of incremental is low and the cost of unnecessary churn is high.

**Alternatives considered.**
- Always full re-cluster — stable identities matter more than marginal accuracy gains.
- Pure incremental, no full mode — incremental drift is real over many runs.

**Trade-offs accepted.** Incremental can entrench bad assignments. Mitigation: low-confidence flags surface candidates for manual re-assignment; `cluster --full` is cheap because embeddings stay cached.

**Related.** [cluster-structural spec](../specs/cluster-structural/spec.md).
