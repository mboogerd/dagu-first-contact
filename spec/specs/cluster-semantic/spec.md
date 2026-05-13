# Cluster — Semantic (Stage 3b)

Generate human-readable summaries for each cluster. LLM-driven but cached.

**Phase.** Stage 3b.

**Input → Output.** `clusters/<cluster>/members.yaml` + member docs and their extractions → `clusters/<cluster>/summary.md` (+ orphan cluster name updates in `clusters/_index.yaml`).

---

## Behavior

- For each cluster, generate `summary.md` covering responsibilities and interactions, from member docs and their extractions.
- Orphan clusters additionally get a meaningful name (replacing `orphan-<index>`) generated from their summary; the rename is recorded in `_index.yaml`.
- Cache key: `hash(sorted(member_content_hashes) + prompt_version + model)`.
- Summary only regenerates when membership or member content changes.

## Cluster summary shape

Free-form markdown. The summary feeds:

- [cluster-hierarchy](../cluster-hierarchy/spec.md) (super-cluster identification).
- [consolidate](../consolidate/spec.md) (as context for criticality assessment).
- [cross-cluster](../cross-cluster/spec.md) (as context for verification).
- [report](../report/spec.md) (landscape section).

Each summary should cover, at minimum:

- **Purpose.** What this cluster represents.
- **Responsibilities.** What its members do collectively.
- **Interactions.** Who it talks to (other clusters, external systems).
- **Notable concerns.** Anything that doesn't fit but the consultant should know.

The exact section structure is not contracted (the cluster's content drives it), but downstream consumers expect the four bullet topics above to be addressable.

## Related decisions

- [D-9](../../decisions/0009-hash-keyed-summary-cache.md) summary cache key.

## Failure modes

- **Generic summaries on heterogeneous clusters.** A cluster with mixed contents produces a vague summary. Acceptable: vagueness is signal that the cluster may need splitting (a concern for [cluster-hierarchy](../cluster-hierarchy/spec.md) or manual review).
- **Stale summary after member-content edits.** Cache key is on member content hashes; edits invalidate correctly.
