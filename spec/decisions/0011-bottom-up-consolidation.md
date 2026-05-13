# [D-11] Bottom-up consolidation

**Status.** Accepted.

**Decision.** Consolidate leaf clusters first; parents reuse children's consolidated outputs.

**Rationale.** Cheaper, cacheable, follows the cluster hierarchy.

**Alternatives considered.**
- Global consolidation in one pass — won't scale; loses cluster context.

**Trade-offs accepted.** Cross-cluster conflicts only surface at common ancestor — addressed by the separate [cross-cluster](../specs/cross-cluster/spec.md) stage.

**Related.** [consolidate spec](../specs/consolidate/spec.md); [D-40](0040-cross-cluster-as-separate-stage.md).
