# Embedding (cross-cutting)

Compute and store embeddings for normalized documents and (downstream) for requirement statements during consolidation. Cross-cutting; supports clustering (Stage 3) and consolidation grouping (Stage 4) and cross-cluster reconciliation (Stage 4.5).

**Phase.** Cross-cutting (no single pipeline stage owns it).

**Input → Output.** `normalized/<source>/<id>.md` → `normalized/<source>/<id>.embedding.json`.

---

## Behavior

Every `NormalizedDoc` has a sidecar embedding file at `<source_id>.embedding.json` containing the vector and its provenance.

The embedding worker:

1. Reads the normalized doc.
2. Computes the appropriate prefix for the task (`clustering: ` for clustering use; `grouping: ` for consolidation grouping; family-specific).
3. Calls the pinned embedding model.
4. Writes the sidecar.

The worker is idempotent: it recomputes only when any of `content_hash`, `embedding_model.name`, `embedding_model.revision`, or `prefix_applied` differs from what's already in the sidecar.

Downstream stages **read** sidecars; they don't call the embedding model directly. If a sidecar is missing or stale, the consuming stage triggers the worker.

## Data shapes

### Embedding sidecar (`<source_id>.embedding.json`)

```json
{
  "source_type": "jira",
  "source_id": "PROJ-123",
  "content_hash": "<NormalizedDoc.content_hash>",
  "embedding_model": {
    "name": "nomic-embed-text-v1.5",
    "revision": "<HF commit SHA>",
    "quant": "Q8_0",
    "dimension": 768
  },
  "prefix_applied": "clustering: ",
  "vector": [0.0123, -0.0456, "..."],
  "embedded_at": "<ISO timestamp>"
}
```

### Prefix convention

Embedding models in the Nomic family require task-specific prefixes (e.g., `search_document: `, `clustering: `). The embedding wrapper SHALL apply the prefix appropriate to the task; the applied prefix is recorded in `prefix_applied` so divergence is detectable. Other model families that don't use prefixes record `prefix_applied: ""`.

### Cache behavior

The embedding sidecar is re-computed when any of `content_hash`, `embedding_model.name`, `embedding_model.revision`, or `prefix_applied` changes. Otherwise it is reused.

## Configuration

In `config/clustering.yaml` (the embedding wrapper shares config with clustering since they're so tightly coupled):

```yaml
embedding:
  name: nomic-embed-text-v1.5
  hf_repo: nomic-ai/nomic-embed-text-v1.5-GGUF
  revision: <40-char HF commit SHA>
  quant: Q8_0
  dimension: 768
  prefix: "clustering: "      # default; downstream consumers may request alternates
  vendored_path: models/embeddings/nomic-embed-text-v1.5.Q8_0.gguf
  expected_sha256: <sha256 of the GGUF file>
```

The GGUF file is **vendored** into `models/embeddings/` for reproducibility. The expected SHA-256 is verified on load.

## Multiple prefixes per doc

A normalized doc may need embeddings with different prefixes for different consumers:

- `clustering: ` for [cluster-structural](../cluster-structural/spec.md).
- `grouping: ` for [consolidate](../consolidate/spec.md) and [cross-cluster](../cross-cluster/spec.md).

The current design stores **one sidecar per (doc, prefix)** pair: the file path includes the prefix when it's not the default. The default sidecar (`<source_id>.embedding.json`) uses `clustering: `; alternates are at `<source_id>.embedding.<prefix>.json`.

[NEEDS CLARIFICATION: The v0 spec was silent on how multiple prefixes per doc are stored. Confirm this approach before implementation, or pick a different convention.]

## Related decisions

- [D-24](../../decisions/0024-local-embedding-model-pinned-and-vendored.md) pinned local model.
- [D-25](../../decisions/0025-embedding-sidecar-files.md) sidecar storage.

## Related risks

- [R-12](../../risks.md) local model quality below frontier.
