# [D-28] Incremental re-clustering by default; full re-cluster on demand

**Status.** Accepted.

**Decision.** Domain assignments are stable across runs by default: new docs are assigned to existing domains via the same nearest-seed + HDBSCAN logic, but existing assignments are not revisited. A `--full` flag forces a complete re-assignment from scratch. A full re-assignment is automatically triggered when `embedding.revision`, `similarity.assignment_threshold`, or HDBSCAN params change.

**Rationale.** Domain identity stability matters during an iterative assessment. New evidence usually fits existing domains; the cost of incremental is low and the cost of unnecessary churn is high.

**Alternatives considered.**
- Always full re-assignment — stable identities matter more than marginal accuracy gains.
- Pure incremental, no full mode — incremental drift is real over many runs.

**Trade-offs accepted.** Incremental can entrench bad assignments. Mitigation: low-confidence flags surface candidates for manual re-assignment; `cluster --full` is cheap because embeddings stay cached.

**Related.** [domain-structural spec](../specs/domain-structural/spec.md).
