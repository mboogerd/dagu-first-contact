# Orchestration (Stage 5)

Sequence stages with incremental, content-addressed execution.

**Phase.** Stage 5 (the runner itself).

**Approach.** Plain Python entrypoint, explicit subcommands. No external workflow engine.

---

## Subcommands

```bash
python -m assessment ingest             # idempotent; only fetches changed sources; runs git repo summarization
python -m assessment taxonomy:discover  # runs Stage 1.5 discovery loop; writes taxonomy/proposal.md
python -m assessment taxonomy:lock      # reads (possibly edited) proposal; writes config/taxonomy.locked.yaml
python -m assessment extract            # refuses to run without locked taxonomy
python -m assessment embed              # refreshes stale embedding sidecars only; idempotent
python -m assessment cluster            # phases 3a-3c in current re-clustering mode (default: incremental)
python -m assessment cluster --full     # forces full re-cluster from scratch
python -m assessment consolidate        # Stage 4 (bottom-up) + Stage 4.5 (cross-cluster) + review_queue.json
python -m assessment consolidate --no-cross-cluster   # skips Stage 4.5; equivalent to cross_cluster.enabled=false
python -m assessment report             # Stage 5.5: writes reports/<ISO_timestamp>.md
```

Discovery and lock are deliberately separate commands. `discover` is reproducible (caches its LLM calls); `lock` is a human-gated step.

## Each stage

- Reads its inputs.
- Computes a content hash of inputs.
- Skips work if outputs exist and input hashes match.
- Writes outputs.

This gives `make`-like incremental behavior without `make`.

## Cache mechanics

The LLM call cache lives at `cache/<hash>.json`. Each entry's key is:

```
hash(prompt_text + input_payload + model_id + schema_id + extra_context)
```

Where `extra_context` includes any stage-specific variant that should invalidate the entry (e.g., `locked_taxonomy_version` for extraction). The cache is committed to git so re-runs across consultants are free.

**Prompt versioning** is part of cache keys. Each prompt template carries a version hash in its frontmatter; editing a prompt produces a new version, which invalidates downstream cache entries.

## Configuration files

```
config/
├── sources.yaml              # what to ingest
├── models.yaml               # which model for which step, pinned versions
├── taxonomy.starting.yaml    # starting taxonomy (floor)
├── taxonomy.locked.yaml      # locked taxonomy produced by taxonomy:lock
├── clustering.yaml           # embedding model, threshold, HDBSCAN params, seed
├── consolidation.yaml        # source authorities, confidence weights, etc.
├── report.yaml               # top-N size, freshness thresholds, section toggles
└── prompts/                  # versioned prompt templates
    ├── summarize_repo.md
    ├── discover_taxonomy.md
    ├── extract_requirements.md
    ├── extract_interactions.md
    ├── extract_domains.md
    ├── group_requirements.md
    ├── reconcile_group.md
    ├── assess_criticality.md
    ├── verify_cross_cluster_conflict.md
    └── label_cluster.md
```

## Models config (`config/models.yaml`)

Pins exact model IDs for every LLM-driven step. No `*-latest` aliases.

[NEEDS CLARIFICATION: The exact shape of `models.yaml` was not fully specified in v0 (it referenced the file but didn't give a schema). Specify in the change folder that introduces orchestration.]

## Related decisions

- [D-12](../../decisions/0012-pinned-model-versions.md) pinned model versions.
- [D-14](../../decisions/0014-deterministic-orchestration.md) deterministic orchestration.
- [D-15](../../decisions/0015-stage-level-incremental-execution.md) stage-level incremental.

## Failure modes

- Hidden state in adapters (e.g., API rate-limit retries that aren't deterministic).
- Cache invalidation bugs — output exists but inputs changed in a way the hash didn't catch.
- Partial failures leaving inconsistent state (e.g., half a cluster's docs re-extracted, half not). Mitigation: stage operations are per-document; resume is safe.
