# [D-25] Embeddings stored as sidecar files

**Status.** Accepted.

**Decision.** Each `NormalizedDoc` has a co-located sidecar at `<source_id>.embedding.json` containing the vector and its provenance (model, revision, prefix, content hash).

**Rationale.** Aligns with filesystem-as-DB ([D-1]). Greppable, diffable, easy to inspect. Each sidecar is independently cacheable on its `content_hash` + model revision. Refreshing one embedding doesn't touch others.

**Alternatives considered.**
- Single `embeddings/` directory mirroring `normalized/` — marginal benefit; loses co-location.
- Single binary index (Parquet, numpy memmap) — breaks filesystem-as-DB ethos. Better choice if scale grows beyond medium.

**Trade-offs accepted.** Many small files. At medium scale (~few thousand docs × ~10KB sidecar each = ~tens of MB) this is fine. See [R-8](../risks.md).

**Related.** [embedding spec](../specs/embedding/spec.md); [D-1](0001-filesystem-as-db.md).
