# Glossary

Central glossary of terms used across the spec. Organized by area.

---

## Pipeline concepts

| Term | Definition |
|---|---|
| **Assessment** | A single engagement's analysis of a client's software system. The pipeline produces artifacts for one assessment at a time. |
| **Evidence** | Raw, immutable input artifacts fetched by adapters. Lives in `evidence/`. Never mutated by downstream stages. |
| **Projection** | A named, parameterized operation that takes an evidence record and produces one or more downstream-ready normalized documents. See [D-49](decisions/0049-projection-primitive.md). |
| **Projection output** | A markdown file with YAML frontmatter produced by a projection. Lives in `projections/`. The unit that downstream stages consume. |
| **Adapter** | A per-source-type module responsible for fetching raw evidence. One adapter per source type (git, jira, rfp, spreadsheet, transcript). |
| **Intent** | A projection-level declaration of whether the evidence describes built state (`implemented`), committed-but-unbuilt state (`planned`), discussed state (`proposed`), or mixed. See [D-50](decisions/0050-source-declared-intent.md). |

## Extraction

| Term | Definition |
|---|---|
| **Requirement** | A structured record extracted from a projection output. Carries `type`, `status`, `statement`, and provenance. |
| **Interaction** | A runtime-topology relationship between two software components. Scoped to runtime; excludes human collaboration and build-time dependencies. |
| **Concept** | A named concept the system organizes itself around. Two kinds: `business_concept` (business capability) and `technical_concept` (implementation area). Formerly called "Domain" in the extraction context (renamed to avoid confusion with the grouping concept). |

## Domain assignment (clustering)

| Term | Definition |
|---|---|
| **Domain** | A grouping of related projection outputs, organized as a folder in `domains/`. Formerly called "cluster." Seeded from git repos; non-git docs assigned by embedding similarity. |
| **Seed domain** | A domain created from a projection output whose contract declares it as a seed source (v1: `git:repo_summary` only). Named after the git repo. |
| **Orphan domain** | A domain discovered by HDBSCAN from unassigned docs that don't match any seed domain. Gets a placeholder name until [domain-semantic](specs/domain-semantic/spec.md) labels it. |
| **Super-domain** | A grouping of sibling domains that share a parent concern. Created by [domain-hierarchy](specs/domain-hierarchy/spec.md) (experimental in v1). |
| **Domain tree** | The hierarchical organization of domains, with leaf domains containing member docs and super-domains grouping siblings. |

## Consolidation

| Term | Definition |
|---|---|
| **RequirementGroup** | A set of requirements from different sources that describe the same thing. Produced by two-stage grouping (embedding pre-grouping + LLM verification). Stored as a per-group markdown file. |
| **Conflict** | A disagreement within a group. Explicit kinds: `contradiction`, `scope_mismatch`, `status_disagreement`, `version_skew`, `type_disagreement`. |
| **Confidence** | A deterministic score (0-1) measuring how well-supported a consolidated requirement is. Computed from five signals; not LLM-generated. |
| **Criticality** | An LLM-assessed level (`critical`, `important`, `moderate`, `minor`) of how central a requirement is to its domain's purpose. |
| **Review priority** | The score that orders the review queue. Default formula: `criticality_numeric * (1 - confidence)`. Higher = more worth a human's time. |
| **Cross-domain finding** | A conflict detected between consolidated requirements in different domains during the bottom-up traversal (phase 4f). Only `contradiction` and `scope_mismatch` kinds. |

## Taxonomy

| Term | Definition |
|---|---|
| **Starting taxonomy** | The initial set of enum values for extraction (requirement types, statuses, interaction kinds, etc.). The floor that discovery refines. |
| **Locked taxonomy** | The reviewed and accepted taxonomy produced by `taxonomy:lock`. Downstream stages refuse to run without it. |
| **Discovery** | The Stage 1.5 process that samples projection outputs and proposes additions/refinements to the starting taxonomy. |

## Infrastructure

| Term | Definition |
|---|---|
| **Content hash** | SHA-256 of an entire file (frontmatter + body for projection outputs). Used as cache keys throughout. |
| **Embedding sidecar** | A `.embedding.json` file co-located with a projection output, containing the vector and its provenance. |
| **Cache key** | A hash of all inputs to an LLM call or stage computation. Ensures re-runs with identical inputs are free. |

## Spec conventions

| Term | Definition |
|---|---|
| **`[D-N]`** | Reference to design decision N. |
| **`[R-N]`** | Reference to risk N. |
| **`[NEEDS CLARIFICATION: ...]`** | A marker flagging a silent assumption that must be resolved before implementation. |
| **`[P]`** | A task marker indicating the task can run in parallel with adjacent same-numbered tasks. |
| **Change folder** | The unit of new work: `changes/<NNN>-slug/` containing proposal, design, tasks, and spec deltas. |
