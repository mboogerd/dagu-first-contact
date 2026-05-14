# [D-11] Bottom-up consolidation

**Status.** Accepted.

**Decision.** Consolidate leaf domains first; parents reuse children's consolidated outputs.

**Rationale.** Cheaper, cacheable, follows the domain hierarchy.

**Alternatives considered.**
- Global consolidation in one pass — won't scale; loses domain context.

**Trade-offs accepted.** Cross-domain conflicts only surface at the common ancestor during the bottom-up traversal — the cross-domain findings pass (phase 4f of consolidate) addresses this at each non-leaf domain.

**Related.** [consolidate spec](../specs/consolidate/spec.md).
