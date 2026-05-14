# Delta — embedding

## MODIFIED

### Sidecar location

Embedding sidecars co-locate with their projection output, not in a separate normalized tree:

```
projections/<source>/<id>/<projection>/
├── <output>.md
└── <output>.embedding.<prefix>.json   ← prefix encoded in filename when non-default
```

When only one prefix is in use (the common case), the prefix suffix is omitted and the file is named `<output>.embedding.json` (keyed to the default `clustering: ` prefix). Multiple prefixes coexist by adding the suffix; this resolves the v1 `[NEEDS CLARIFICATION]` in the embedding spec.

### Cache invalidation

The embedding sidecar is re-computed when any of `content_hash`, `embedding_model.name`, `embedding_model.revision`, or `prefix_applied` changes — unchanged from v0.

Additionally, the embedding worker SHOULD record `projection: <adapter>:<projection>` and `projection_version` in the sidecar's metadata block, so that consumers can correlate an embedding back to its projection without re-reading the markdown.

## REMOVED

- The `[NEEDS CLARIFICATION]` marker about how multiple prefixes per doc are stored. Resolved by the per-projection sidecar location described above.

## ADDED

Nothing structural. The change is purely about *where* sidecars live and how the embedding records its projection provenance.

## Related

- [Change folder 001](../../changes/001-projection-primitive/proposal.md) §Embedding implications.
