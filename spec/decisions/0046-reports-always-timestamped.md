# [D-46] Reports are always timestamped and never overwritten

**Status.** Accepted.

**Decision.** Each `report` invocation writes a new file `reports/<ISO_timestamp>.md` (UTC, filename-safe form). Existing reports are never overwritten. There is no canonical "current" `report.md`.

**Rationale.** The consultant explicitly chose timestamped reports over git-history-based versioning. Every report is a durable snapshot. Reports referencing specific pipeline state at the moment of generation should not be edited or replaced.

**Alternatives considered.**
- Single `report.md` overwritten in place, git tracks history — rejected by the consultant in favor of explicit snapshots.
- Hybrid: `report.md` current plus `reports/<timestamp>.md` on demand — complicates the mental model.

**Trade-offs accepted.** Disk accumulation over many iterations. Mitigation: gitignore by default; commit only meaningful snapshots. See [R-24](../risks.md).

**Related.** [report spec](../specs/report/spec.md).
