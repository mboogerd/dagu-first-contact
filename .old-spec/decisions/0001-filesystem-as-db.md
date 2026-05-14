# [D-1] Filesystem-as-DB

**Status.** Accepted.

**Decision.** Use the filesystem as the primary store; commit everything to git.

**Rationale.** For a one-shot consulting assessment at medium scale, filesystem beats any DB on simplicity, greppability, diffability, portability, and reproducibility. Git tracks the full state.

**Alternatives considered.**
- SQLite — more queryable but binary; loses greppability.
- DuckDB+Parquet — good for analytics but adds tooling.
- Vector DB — overkill at this scale.

**Trade-offs accepted.** Cross-document queries require ad-hoc scripts. Acceptable: queries are infrequent and the consultant is the user.

**Related.** Principle 1 in [principles.md](../principles.md).
