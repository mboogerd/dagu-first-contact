# [D-38] Layered consolidation caching by content addressing

**Status.** Accepted.

**Decision.** Consolidation cache operates at three levels: grouping (keyed on member content hashes + grouping config), conflict detection (keyed on group inputs), and criticality (keyed on statement + cluster summary hash). Each level invalidates independently. Changes to `config/consolidation.yaml` invalidate only the levels affected by the changed sections.

**Rationale.** Consolidation is the most expensive stage (expensive reasoning model per [D-13]). Coarse caching would force full re-consolidation on small config edits; no caching would make iteration cost-prohibitive. Layered caching makes the cost of a change proportional to its scope.

**Alternatives considered.**
- Single cache key over all consolidation inputs — any config edit triggers full re-consolidation.
- No cache — cost-prohibitive.

**Trade-offs accepted.** Cache invalidation logic is the most complex in the spec. Mitigation: each cache level is content-addressed and independently testable.

**Related.** [consolidate spec](../specs/consolidate/spec.md).
