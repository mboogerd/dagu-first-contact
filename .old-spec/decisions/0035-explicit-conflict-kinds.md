# [D-35] Conflict has explicit kinds with mixed deterministic and LLM detection

**Status.** Accepted.

**Decision.** `Conflict.kind` is an enum (`contradiction | scope_mismatch | status_disagreement | version_skew | type_disagreement`). Status/type disagreements are detected deterministically from structured fields; version skew is detected deterministically (date spread) and confirmed by LLM; contradiction and scope mismatch are detected by LLM only. A single group can have multiple conflicts of different kinds.

**Rationale.** "Is there a conflict?" is a worse question than "what kind of conflict, and what's the evidence?" Different kinds need different detection (cheap structured checks vs. expensive LLM reasoning) and different review treatment. Explicit kinds also make the review queue filterable.

**Alternatives considered.**
- Single boolean `conflict.present` — loses signal.
- Free-text conflict descriptions only — not filterable.
- LLM-only detection for all kinds — wastes tokens on disagreements that are obvious from structured fields.

**Trade-offs accepted.** Five kinds is a small taxonomy that may need extension. Acceptable: extending the kind enum is a config-level change.

**Related.** [consolidate spec](../specs/consolidate/spec.md).
