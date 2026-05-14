# [D-51] Adapter registry with co-located per-adapter config

**Status.** Accepted.

**Decision.** Each source-type adapter is a registered module under `assessment/adapters/<adapter-name>/` containing its implementation and an `adapter.yaml` manifest. The adapter name (e.g., `git`, `jira`, `rfp`) serves as the directory key under `evidence/`, `projections/`, `extracted/`, and as the `adapter` frontmatter field in projection outputs. The former `source_type` enum is retired; the adapter name is just the directory name.

Per-adapter configuration — notably `authority_weight` (used in consolidation reconciliation and confidence scoring) and `default_evidence_strength` — lives in the adapter's `adapter.yaml` manifest rather than in `consolidation.yaml`. This means adding a new source type is fully self-contained: create one adapter directory, no edits to distant config files. Per-assessment overrides are still available via `consolidation.yaml: source_authority_overrides`.

**Rationale.** `source_type` was an enum spread across adapters, frontmatter, source-authority weights, and prompts. In most of those places it functioned as "name of the directory the artifact came from." Making the adapter name the single source of truth — directory name, frontmatter field, config key — removes the implicit enum and makes the system open for extension without modification.

The projection registry ([D-49](0049-projection-primitive.md)) established the pattern; the adapter registry is the natural parallel.

**Alternatives considered.**
- Keep the enum — workable for five source types but doesn't scale; every new source type requires edits in multiple locations.
- Central `config/adapters.yaml` registry file — still decouples the adapter's identity from its implementation. The co-located `adapter.yaml` is simpler.

**Trade-offs accepted.** Authority weights are now distributed across adapter directories instead of visible in one config block. Mitigation: `consolidation.yaml: source_authority_overrides` provides a single place for per-assessment tuning; the adapter defaults are visible via `assessment/adapters/*/adapter.yaml`.

**Related.** [ingest spec](../specs/ingest/spec.md); [D-3](0003-adapter-pattern-for-ingestion.md); [D-49](0049-projection-primitive.md).
