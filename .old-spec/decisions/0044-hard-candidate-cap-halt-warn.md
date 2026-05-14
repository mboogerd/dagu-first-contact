# [D-44] Hard candidate cap with halt-and-warn

**Status.** Accepted.

**Decision.** The cross-domain pre-filtering enforces `cross_domain.max_candidate_pairs` (default 500). If exceeded, the stage halts with a warning rather than proceeding silently. The consultant decides whether to raise the threshold (reducing candidate count) or raise the cap (accepting the cost).

**Rationale.** A corpus that produces 10,000 candidate pairs is signaling something. Both situations (low threshold, or many legitimately similar requirements) warrant consultant judgment. Halting is louder than silent expensive runs.

**Alternatives considered.**
- No cap — pathological corpora produce runaway cost.
- Soft cap with sampling — introduces randomness; hard to reproduce.
- Auto-raise threshold until under cap — hides the signal that something is off.

**Trade-offs accepted.** A first-run halt is disruptive. Acceptable: the warning is informative; the fix (raising threshold) is a one-line config change followed by a re-run, which is cheap because cached embeddings persist.

**Related.** [consolidate spec](../specs/consolidate/spec.md); [R-21](../risks.md).
