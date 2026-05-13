# [D-14] Deterministic orchestration, LLMs as workers

**Status.** Accepted.

**Decision.** Pipeline graph (ingest → extract → cluster → consolidate) is fixed code. LLMs are called from within stages, not asked to orchestrate stages.

**Rationale.** Reproducibility, debuggability, cost predictability. Agent orchestration adds non-determinism exactly where it's most harmful.

**Alternatives considered.**
- Agent-based orchestration — initially considered; rejected (see [R-1](../risks.md)).

**Trade-offs accepted.** Less "smart" — the pipeline can't decide to skip a stage or re-route based on findings. A user-facing chat agent over the results is a separate concern.

**Related.** Principle 5 in [principles.md](../principles.md); [orchestration spec](../specs/orchestration/spec.md).
