# Decisions

One file per design decision (ADR-style). Numbers match the original `[D-N]` references from the v0 monolith and are not reused.

Decisions dropped or deferred for v1 are not present here. Their numbers are preserved (skipped) so the surviving cross-references remain unambiguous. See [open-questions.md](../open-questions.md) for what was deferred.

## Index

| # | Title | Component |
|---|---|---|
| [D-1](0001-filesystem-as-db.md) | Filesystem-as-DB | (principles) |
| [D-2](0002-uniform-normalized-doc-shape.md) | Uniform normalized-doc shape | ingest |
| [D-3](0003-adapter-pattern-for-ingestion.md) | Adapter pattern for ingestion | ingest |
| [D-4](0004-source-agnostic-extractors.md) | Source-agnostic extractors | extract |
| [D-5](0005-structured-outputs-only.md) | Structured outputs only | (principles) |
| [D-7](0007-embeddings-first-clustering.md) | Embeddings-first clustering | domain-structural |
| [D-8](0008-git-repos-as-cluster-seeds.md) | Git repos as domain seeds | domain-structural |
| [D-9](0009-hash-keyed-summary-cache.md) | Hash-keyed summary cache | domain-semantic |
| [D-10](0010-provenance-driven-conflict-resolution.md) | Provenance-driven conflict resolution | consolidate |
| [D-11](0011-bottom-up-consolidation.md) | Bottom-up consolidation | consolidate |
| [D-12](0012-pinned-model-versions.md) | Pinned model versions | orchestration |
| [D-13](0013-expensive-model-at-consolidation-only.md) | Expensive model only at consolidation | (principles) |
| [D-14](0014-deterministic-orchestration.md) | Deterministic orchestration, LLMs as workers | (principles) |
| [D-15](0015-stage-level-incremental-execution.md) | Stage-level incremental execution | orchestration |
| [D-16](0016-three-explicit-extractors.md) | Three explicit extractors with distinct schemas | extract |
| [D-17](0017-bounded-discovery-termination.md) | Bounded taxonomy-discovery termination | taxonomy |
| [D-18](0018-starting-taxonomy-as-floor.md) | Starting taxonomy is a floor | taxonomy |
| [D-19](0019-discovery-blocks-extract.md) | Taxonomy discovery blocks Extract | taxonomy |
| [D-20](0020-human-reviewed-lock.md) | Human-reviewed lock via diff proposal | taxonomy |
| [D-21](0021-taxonomy-debt-post-lock.md) | Taxonomy debt found post-lock is documented | taxonomy |
| [D-22](0022-git-repo-curated-summary.md) | ~~Git-repo curated summary~~ | ~~ingest~~ Superseded by D-49 |
| [D-23](0023-raw-evidence-accessible-to-extractors.md) | Raw evidence accessible to extractors | extract |
| [D-24](0024-local-embedding-model-pinned-and-vendored.md) | Local embedding model pinned & vendored | embedding |
| [D-25](0025-embedding-sidecar-files.md) | Embedding sidecar files | embedding |
| [D-26](0026-single-global-similarity-threshold.md) | Single global similarity threshold | domain-structural |
| [D-27](0027-hdbscan-over-unassigned-only.md) | HDBSCAN over unassigned only | domain-structural |
| [D-28](0028-incremental-reclustering-by-default.md) | Incremental re-clustering by default | domain-structural |
| [D-34](0034-two-stage-requirement-grouping.md) | Two-stage requirement grouping | consolidate |
| [D-35](0035-explicit-conflict-kinds.md) | Explicit conflict kinds | consolidate |
| [D-36](0036-deterministic-confidence.md) | Deterministic confidence | consolidate |
| [D-37](0037-discrete-criticality-scale.md) | Discrete criticality scale | consolidate |
| [D-38](0038-layered-consolidation-caching.md) | Layered consolidation caching | consolidate |
| [D-40](0040-cross-cluster-as-separate-stage.md) | Cross-domain detection in bottom-up traversal | consolidate (cross-domain) |
| [D-41](0041-cross-cluster-conservative-scope.md) | Cross-domain conservative scope (flagged) | consolidate (cross-domain) |
| [D-42](0042-annotations-as-sidecar-files.md) | Cross-domain findings as markdown files | consolidate (cross-domain) |
| [D-43](0043-cross-cluster-always-runs.md) | Cross-domain detection always runs | consolidate (cross-domain) |
| [D-44](0044-hard-candidate-cap-halt-warn.md) | Hard candidate cap (halt-and-warn) | consolidate (cross-domain) |
| [D-45](0045-deterministic-report-rendering.md) | Deterministic report rendering | report |
| [D-46](0046-reports-always-timestamped.md) | Reports always timestamped | report |
| [D-47](0047-freshness-signals-first-class.md) | Freshness signals are first-class | report |
| [D-48](0048-report-sections-independent-and-toggleable.md) | Independent toggleable report sections | report |
| [D-49](0049-projection-primitive.md) | Projection primitive | ingest |
| [D-50](0050-source-declared-intent.md) | Source-declared intent | ingest, consolidate |
| [D-51](0051-adapter-registry.md) | Adapter registry with co-located config | ingest |

## Numbers retained but decisions dropped/deferred in v1

| # | Original title | Status |
|---|---|---|
| D-6 | Per-extractor eval set | Deferred — eval framework not in v1. See [open-questions.md](../open-questions.md). |
| D-29..D-33 | Eval framework details | Deferred. |
| D-39 | Calibration loop | Deferred. |
| D-52 | Cluster archival semantics | Deferred — not needed in PoC timeframe. D-49, D-50, D-51 were reassigned. |
