# [D-40] Cross-domain detection runs during bottom-up consolidation with a priority boost

**Status.** Accepted (revised — cross-domain detection is now phase 4f of consolidate, not a separate stage).

**Decision.** Cross-domain conflict detection runs as part of the bottom-up consolidation traversal. At each non-leaf domain, after gathering children's consolidated outputs, an additional pass detects `contradiction` and `scope_mismatch` conflicts between children's consolidations. Findings land in the lowest common ancestor domain's folder as `<domain-name>__cross-domain-findings.md`. Participating items receive a `cross_domain_boost` (default 0.20) to their `review_priority`.

**Rationale.** Conflicts between sibling domains are missed by within-domain consolidation; detecting them during the bottom-up traversal is the natural integration point. The priority boost is the mechanism by which cross-domain findings reach the consultant.

**Alternatives considered.**
- Separate stage after consolidation (original design) — dissolved into the traversal for simplicity.
- No priority boost; just publish findings in a separate artifact — cross-domain findings have higher review value and should be prioritized accordingly.

**Trade-offs accepted.** The boost magnitude (0.20) is a guess in v1 — calibration is deferred. Acceptable: cost is bounded by `max_candidate_pairs`; cache reuse on stable inputs makes re-runs cheap.

**Related.** [consolidate spec](../specs/consolidate/spec.md); [R-23](../risks.md).
