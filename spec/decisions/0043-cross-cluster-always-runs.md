# [D-43] Cross-cluster reconciliation always runs by default; config-gated for cost

**Status.** Accepted.

**Decision.** Cross-cluster reconciliation runs as part of every `consolidate` command by default. It can be disabled via `config/consolidation.yaml: cross_cluster.enabled: false` (config-level) or `--no-cross-cluster` (per-invocation). Disabling preserves consolidate outputs untouched; no annotations are written; review_queue.json is regenerated without cross-cluster contributions.

**Rationale.** Cross-cluster findings are the kind of thing easy to forget to run, and forgetting silently produces an inferior review queue. Making it the default protects against that. The config and CLI gates exist for cost-bounded runs.

**Alternatives considered.**
- Always opt-in — easy to skip.
- Always runs with no opt-out — legitimate iteration scenarios shouldn't pay the full cost every time.

**Trade-offs accepted.** Default cost is higher than per-cluster-only consolidation. Acceptable: cached candidates and verifications make re-runs cheap once the first run is done.

**Related.** [cross-cluster spec](../specs/cross-cluster/spec.md).
