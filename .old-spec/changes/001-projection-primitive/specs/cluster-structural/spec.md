# Delta — cluster-structural

## MODIFIED

### Input location

Cluster-structural reads embedding sidecars from `projections/<source>/<id>/<projection>/<output>.embedding.json` instead of `normalized/<source>/<id>.embedding.json`.

### Seeding

The seed-cluster rule changes from "one cluster per git repo" to **"one cluster per output of every projection whose contract declares it as a seed source."**

In v1, `git:repo_summary` is the only projection that declares itself a seed. Behavior is therefore unchanged: one cluster per non-archived git repo, seeded from the `git:repo_summary` output.

Adding a new seed projection is a future change that flips the declaration in the projection contract; no code change to clustering is needed.

### Assignment unit

The unit of assignment is a **projection output**, not an evidence record. A single piece of evidence with multiple projections (e.g., RFP with `whole_document` and `section_split`) contributes multiple assignment candidates. Each projection output gets its own row in `clusters/_assignments.json`.

This means an RFP that splits into 5 sections via `rfp:section_split` AND emits a single `rfp:whole_document` produces 6 assignment rows — 5 partials potentially landing in different clusters, plus the whole-document potentially landing in yet another (or being unassigned). The consultant interprets these as legitimately different views of the same evidence.

### Assignment record

The `clusters/_assignments.json` schema gains a `projection` field:

```json
{
  "source_type": "rfp",
  "source_id": "doc-12",
  "projection": "rfp:section_split",
  "projection_output": "03-payments-integration.md",
  "cluster_path": "clusters/payments-service",
  "similarity": 0.71,
  "low_confidence": false,
  "method": "nearest_seed | hdbscan_orphan | manual_override"
}
```

`projection_output` is the filename within the projection's folder. Together with `source_type`, `source_id`, and `projection`, it uniquely identifies a projection output.

## REMOVED

- No structural removals. Internal references that said "normalized doc" are reworded to "projection output."

## ADDED

### Failure modes (new)

- **Whole-document and partial assignments diverging unhelpfully.** An RFP's `whole_document` projection assigns to cluster X (the dominant subsystem) while one of its `section_split` partials assigns to cluster Y (a different subsystem the section is actually about). Both are correct — the dominant signal vs. the per-section signal. The review queue surfaces both; the consultant decides whether to disable `whole_document` for this RFP via `config/sources.yaml`.

## Related

- [Change folder 001](../../changes/001-projection-primitive/proposal.md).
