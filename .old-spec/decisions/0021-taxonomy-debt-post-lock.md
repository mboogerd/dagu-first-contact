# [D-21] Taxonomy debt found post-lock is documented, not chased

**Status.** Accepted.

**Decision.** If extraction reveals genuine taxonomy gaps after lock, the gap is documented as a known limitation. The run finishes. Re-lock + re-extraction is only triggered if the severity (impact on the review queue) warrants it, judged by the consultant.

**Rationale.** Discovery is a sample-based prior; perfect coverage is not the goal. Restarting extraction on every minor finding produces diminishing returns and inflates costs. The consultant is the right decision-maker for severity.

**Alternatives considered.**
- Auto-restart on any post-lock taxonomy gap — too aggressive.
- No documentation of gaps — loses audit trail.

**Trade-offs accepted.** The final review queue may carry items with sub-optimal `type` or `kind` classifications. Acceptable: the underlying statements and provenance are intact.

**Related.** [taxonomy spec](../specs/taxonomy/spec.md).
