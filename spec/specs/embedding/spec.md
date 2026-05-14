# Embedding (cross-cutting)

Compute and store embeddings for projection outputs and (downstream) for requirement statements during consolidation. Cross-cutting; supports domain assignment (Stage 3) and consolidation grouping (Stage 4).

**Phase.** Cross-cutting (no single pipeline stage owns it).

**Input → Output.** `projections/<source>/<id>/<projection>/<output>.md` → co-located `.embedding.json` sidecar.

---

## Behavior

Every projection output has a sidecar embedding file co-located in the same directory, containing the vector and its provenance.

The embedding worker:

1. Reads the projection output.
2. Computes the appropriate prefix for the task (`clustering: ` for domain assignment use; `grouping: ` for consolidation grouping; family-specific).
3. Calls the pinned embedding model.
4. Writes the sidecar.

The worker is idempotent: it recomputes only when any of `content_hash`, `embedding_model.name`, `embedding_model.revision`, or `prefix_applied` differs from what's already in the sidecar.

Downstream stages **read** sidecars; they don't call the embedding model directly. If a sidecar is missing or stale, the consuming stage triggers the worker.

## Data shapes

### Embedding sidecar

Sidecar files co-locate with their projection output:

```
projections/<source>/<id>/<projection>/
├── <output>.md
├── <output>.embedding.json                  ← default prefix (clustering:)
└── <output>.embedding.grouping.json         ← alternate prefix
```

When only one prefix is in use (the common case), the prefix suffix is omitted and the file is named `<output>.embedding.json` (keyed to the default `clustering: ` prefix). Multiple prefixes coexist by encoding the prefix in the filename.

```json
{
  "source_type": "jira",
  "source_id": "PROJ-123",
  "projection": "jira:bulk_download",
  "projection_version": "<hash>",
  "content_hash": "<projection output content_hash>",
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

In `config/clustering.yaml` (the embedding wrapper shares config with domain assignment since they're tightly coupled):

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

A projection output may need embeddings with different prefixes for different consumers:

- `clustering: ` for [domain-structural](../domain-structural/spec.md).
- `grouping: ` for [consolidate](../consolidate/spec.md).

The sidecar naming convention handles this: the default sidecar (`<output>.embedding.json`) uses the `clustering: ` prefix; alternates use `<output>.embedding.<prefix>.json`.

## Related decisions

- [D-24](../../decisions/0024-local-embedding-model-pinned-and-vendored.md) pinned local model.
- [D-25](../../decisions/0025-embedding-sidecar-files.md) sidecar storage.

## Related risks

- [R-12](../../risks.md) local model quality below frontier.
