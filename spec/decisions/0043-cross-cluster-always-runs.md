# [D-43] Cross-domain detection always runs as part of consolidation

**Status.** Accepted (revised — no longer a separate opt-out; it's an integral part of the bottom-up traversal).

**Decision.** Cross-domain conflict detection runs as part of every `consolidate` command. It is phase 4f of the bottom-up traversal and cannot be independently disabled.

**Rationale.** Cross-domain findings are the kind of thing easy to forget to run, and forgetting silently produces an inferior review queue. Making it integral to the traversal protects against that. The cost is bounded by `max_candidate_pairs` and cache reuse.

**Alternatives considered.**
- Always opt-in — easy to skip.
- Config-gated opt-out (original design) — unnecessary complexity when the cost is bounded.

**Trade-offs accepted.** Every consolidation run pays the cross-domain detection cost. Acceptable: cached candidates and verifications make re-runs cheap once the first run is done.

**Related.** [consolidate spec](../specs/consolidate/spec.md).
