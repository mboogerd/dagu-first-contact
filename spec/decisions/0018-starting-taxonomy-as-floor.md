# [D-18] Starting taxonomy is a floor; removals require human approval

**Status.** Accepted.

**Decision.** `config/taxonomy.starting.yaml` is the floor for discovery. Discovery may add values, refine descriptions, propose removals, and flag ambiguities. **Removals are flagged in the proposal with `requires_human_approval: true` and are not applied silently.**

**Rationale.** A quiet sample (a source type with no `assumption`-flavored statements, say) should not erase a legitimate enum value. The starting taxonomy reflects thought already invested; discovery refines it, doesn't reset it.

**Alternatives considered.**
- Free-form discovery starting from zero — throws away prior thought.
- Discovery as suggestion-only with no auto-application — loses automated finding aggregation.

**Trade-offs accepted.** Legitimately obsolete enum values stay in the taxonomy until the consultant explicitly removes them in proposal review.

**Related.** [taxonomy spec](../specs/taxonomy/spec.md).
