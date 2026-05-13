# [D-20] Human-reviewed lock via diff proposal

**Status.** Accepted.

**Decision.** Discovery output is a human-readable `taxonomy/proposal.md` showing a diff vs. the starting taxonomy. The consultant reviews, edits if needed, then runs `taxonomy:lock` to write `config/taxonomy.locked.yaml`. No interactive prompts; no auto-lock.

**Rationale.** Reviewable, diffable, reproducible. Interactive prompts aren't reproducible (no record of what was accepted and why). Auto-lock skips the deliberate checkpoint that justifies the up-front cost of running discovery at all.

**Alternatives considered.**
- Interactive Y/N prompts — not reproducible; no audit trail.
- Auto-lock with after-the-fact edits — loses the deliberate review step.

**Trade-offs accepted.** Requires the consultant to actually do the review. Mitigated by making the proposal scannable and pre-categorized (high vs. low confidence, supported vs. single-source).

**Related.** [taxonomy spec](../specs/taxonomy/spec.md).
