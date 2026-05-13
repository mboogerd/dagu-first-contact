# [D-3] Adapter pattern for ingestion

**Status.** Accepted.

**Decision.** One adapter per source type, single-purpose: fetch + normalize.

**Rationale.** New source types = new file. No changes to extractors, clustering, or consolidation.

**Alternatives considered.**
- One mega-ingestor with conditional branches.

**Trade-offs accepted.** Some code duplication across adapters (e.g., date parsing).

**Related.** [ingest spec](../specs/ingest/spec.md).
