# [D-15] Stage-level incremental execution

**Status.** Accepted.

**Decision.** Each stage hashes inputs, skips if outputs exist and match. No external build tool.

**Rationale.** `make`-like behavior in Python is cheap; avoids dependency on `make` or a workflow engine.

**Alternatives considered.**
- Prefect/Dagster — overhead too high for one-off assessment.

**Trade-offs accepted.** Custom cache invalidation logic; potential for bugs. Mitigated by keeping the logic small and uniform across stages.

**Related.** [orchestration spec](../specs/orchestration/spec.md).
