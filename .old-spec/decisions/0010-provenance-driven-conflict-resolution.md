# [D-10] Provenance-driven conflict resolution

**Status.** Accepted.

**Decision.** Conflicts resolved by an ordered ruleset: manual override → source authority weights → recency → LLM judgment.

**Rationale.** Deterministic where possible. LLM judgment only as a tiebreaker, with rationale always recorded.

**Alternatives considered.**
- Pure LLM judgment — less defensible to the client.

**Trade-offs accepted.** Source authority weights need configuration and tuning. In v1 they ship as defaults; tuning is the consultant's call mid-assessment.

**Related.** [consolidate spec](../specs/consolidate/spec.md); [R-6](../risks.md).
