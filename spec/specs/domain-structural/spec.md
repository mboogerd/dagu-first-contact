# Domain — Structural (Stage 3a)

Compute domain membership deterministically from embeddings. No LLM calls.

**Phase.** Stage 3a.

**Input → Output.** Projection output embeddings + `config/clustering.yaml` → `domains/_index.yaml` + `domains/_assignments.json` + `domains/<domain>/members.yaml`.

---

## Behavior

Four sub-phases, all deterministic.

### Embedding precondition

- Every projection output has a sidecar embedding (see [embedding spec](../embedding/spec.md)) computed with the pinned model and the `clustering: ` prefix.
- This stage never calls the embedding model directly; it reads sidecars. If a sidecar is missing or stale (model revision mismatch, content_hash mismatch, prefix mismatch), this stage triggers the embedding worker to refresh it.
- Embedding is one vector per projection output. For git, that means the embedding represents the **curated repo summary** (the `git:repo_summary` projection output). See [D-49].

### Seeding

- One domain is seeded per output of every projection whose contract declares it as a **seed source**. In v1, `git:repo_summary` is the only seed projection. Behavior: one domain per non-archived git repo.
- Seed domain name = repo name. `origin: seed`.
- Seed domains are created before any assignment runs.
- Adding a new seed projection is a future change that flips the declaration in the projection contract; no code change to domain assignment is needed.

### Assignment (non-seed projection outputs)

- For each non-seed projection output, compute cosine similarity against every seed domain's embedding.
- Assign to the nearest seed domain IF `similarity >= similarity.assignment_threshold` (default 0.60; see [D-26]).
- If `similarity` falls within `low_confidence_band` (default [0.55, 0.65]), the assignment is recorded with `low_confidence: true` for human review.
- If `similarity < assignment_threshold`, the doc is **unassigned** at this step.

The unit of assignment is a **projection output**, not an evidence record. A single piece of evidence with multiple projections (e.g., RFP with `whole_document` and `section_split`) contributes multiple assignment candidates. Each projection output gets its own row in `domains/_assignments.json`.

This means an RFP that splits into 5 sections via `rfp:section_split` AND emits a single `rfp:whole_document` produces 6 assignment rows — 5 partials potentially landing in different domains, plus the whole-document potentially landing in yet another (or being unassigned).

### Orphan discovery (HDBSCAN on unassigned)

- Run HDBSCAN on the embeddings of all unassigned docs, with parameters from `config/clustering.yaml` (`min_cluster_size`, `min_samples`, `metric: cosine`, `random_seed: 42`).
- Each HDBSCAN cluster with >= `min_cluster_size` members becomes an orphan domain (`origin: orphan`). Its name is a placeholder (`orphan-<index>`) until [domain-semantic](../domain-semantic/spec.md) labels it.
- HDBSCAN noise points (label `-1`) remain unassigned.

### Determinism guarantees

- Same embeddings + same config = same assignments. HDBSCAN seed is fixed; assignment is a deterministic argmax with explicit tie-breaking on `source_id` lexicographic order.
- No LLM calls in this stage.

## Re-clustering policy

This stage operates in one of two modes set in `config/clustering.yaml: reclustering.mode`:

- **`incremental` (default).** Existing assignments are preserved; only new or changed docs are assigned. New seed domains are created when new git repos are added. HDBSCAN runs only over genuinely-new unassigned docs combined with already-unassigned docs. Stable domain identities across runs.
- **`full`.** Discard `_assignments.json`, re-run from scratch. Embeddings are still cached; only assignment changes. Required when `assignment_threshold`, `embedding.revision`, or HDBSCAN params change.

The orchestration subcommand `cluster --full` forces a full re-cluster regardless of config.

## Configuration (`config/clustering.yaml`)

```yaml
version: "<semver or hash>"

embedding:
  # See ../embedding/spec.md for the embedding configuration. Shared file.
  name: nomic-embed-text-v1.5
  hf_repo: nomic-ai/nomic-embed-text-v1.5-GGUF
  revision: <40-char HF commit SHA>
  quant: Q8_0
  dimension: 768
  prefix: "clustering: "
  vendored_path: models/embeddings/nomic-embed-text-v1.5.Q8_0.gguf
  expected_sha256: <sha256 of the GGUF file>

similarity:
  metric: cosine
  assignment_threshold: 0.60         # tunable; see [D-26]
  low_confidence_band: [0.55, 0.65]  # assignments in this band are flagged for review

hdbscan:
  enabled: true
  min_cluster_size: 3
  min_samples: 2
  metric: cosine
  random_seed: 42

reclustering:
  mode: incremental   # incremental | full; see [D-28]
```

## Data shapes

### Domain entry (`domains/_index.yaml`)

```yaml
- name: payments-service
  path: domains/payments-service
  parent: domains/financial-domain   # null if root
  member_count: 47
  summary_hash: <hash of summary inputs>   # cache key for domain-semantic
  seeded_from: git:payments-service        # provenance of domain creation
  origin: seed | orphan                    # seed = projection-derived; orphan = HDBSCAN-discovered
```

### Domain assignment record (`domains/_assignments.json`)

```json
{
  "clustering_version": "<config/clustering.yaml version>",
  "embedding_version": "<embedding.name>@<embedding.revision>",
  "assignments": [
    {
      "source_type": "jira",
      "source_id": "PROJ-123",
      "projection": "jira:bulk_download",
      "projection_output": "PROJ-123.md",
      "domain_path": "domains/payments-service",
      "similarity": 0.71,
      "low_confidence": false,
      "method": "nearest_seed | hdbscan_orphan | manual_override"
    }
  ],
  "unassigned": [
    {"source_type": "transcript", "source_id": "kickoff-2026-03-14",
     "projection": "transcript:speaker_grouped",
     "projection_output": "kickoff-2026-03-14.md",
     "best_similarity": 0.42, "reason": "below_threshold_no_orphan_domain"}
  ]
}
```

## Related decisions

- [D-7](../../decisions/0007-embeddings-first-clustering.md) embeddings-first.
- [D-8](../../decisions/0008-git-repos-as-cluster-seeds.md) git repos as seeds.
- [D-26](../../decisions/0026-single-global-similarity-threshold.md) single global threshold.
- [D-27](../../decisions/0027-hdbscan-over-unassigned-only.md) HDBSCAN scope.
- [D-28](../../decisions/0028-incremental-reclustering-by-default.md) incremental re-clustering.
- [D-49](../../decisions/0049-projection-primitive.md) projection primitive.

## Related risks

- [R-3](../../risks.md) embedding-based assignment misfilings.
- [R-11](../../risks.md) repo summary as single-point-of-failure for seeding.
- [R-12](../../risks.md) local embedding model quality.

## Failure modes

- **Misfiled docs from embedding-only assignment.** A Jira ticket semantically near repo A but actually about repo B. Mitigation: low-confidence band surfaces borderline cases; explicit hints in projection output frontmatter (`assignment_hint`) can override automatic assignment (recorded with `method: manual_override`).
- **Bad repo-summary degrades domain quality.** Since git repos are seeds, a misleading summary contaminates every assignment to that domain. Mitigation: consultant can manually edit the `git:repo_summary` projection output; the embedding refreshes on next run; the next `cluster` run reflects the edit.
- **Embedding model drift between runs.** Two runs with different model revisions produce incomparable embeddings. Mitigation: `config/clustering.yaml` pins the revision and expected SHA-256; embedding sidecars record their model revision so mismatches are detectable and trigger refresh.
- **Threshold mis-tuning.** Too high → many unassigned docs and noisy orphan domains; too low → everything assigned to nearest seed regardless of fit. Mitigation: low-confidence band surfaces borderline assignments; threshold tuning is part of first-run validation.
- **HDBSCAN sensitivity.** Small `min_cluster_size` produces fragmented orphans; large values miss legitimate small subsystems. Defaults (3, 2) are tuned for medium-scale assessments and are adjustable in config.
- **Incremental drift.** Long-running incremental assignment can accumulate suboptimal assignments as the corpus grows. Mitigation: periodic `cluster --full` re-runs (cheap because embeddings stay cached).
- **Whole-document and partial assignments diverging unhelpfully.** An RFP's `whole_document` projection assigns to domain X (the dominant subsystem) while one of its `section_split` partials assigns to domain Y (a different subsystem the section is actually about). Both are correct — the dominant signal vs. the per-section signal. The review queue surfaces both; the consultant decides whether to disable `whole_document` for this RFP via `config/sources.yaml`.
