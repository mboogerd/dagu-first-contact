# Cross-cluster Reconciliation (Stage 4.5)

Detect conflicts between consolidated requirements that live in different cluster subtrees and never share a per-cluster consolidation pass. Surface findings without re-running per-cluster consolidation.

**Phase.** Stage 4.5.

**Input → Output.** All `clusters/**/consolidated/requirements.json` + `config/consolidation.yaml` → `cross_cluster/candidates.json` + `cross_cluster/conflicts.json` + `clusters/**/consolidated/cross_cluster_annotations.json`.

**When it runs.** Always, immediately after [consolidate](../consolidate/spec.md) in `consolidate`. Can be skipped by setting `config/consolidation.yaml: cross_cluster.enabled: false` for cost-bounded runs.

**Status note.** Held in a conservative form for v1: detection runs at high threshold, `needs_review` cases are surfaced, but the priority-boost calibration question is deferred. The default `cross_cluster_boost: 0.20` is a guess and is accepted as-is for v1. See [open-questions.md](../../open-questions.md).

---

## Scope by design

- Detects only `contradiction` and `scope_mismatch` kinds.
- `status_disagreement` and `type_disagreement` are excluded because same-named concepts in different clusters legitimately differ on these dimensions (a "user" in auth ≠ a "user" in analytics).
- `version_skew` is excluded because cross-cluster same-statement-different-time is unusual and noisy.
- Detects only between requirements in **different** clusters (`cluster_distance ≥ 1`). Same-cluster pairs were already handled in [consolidate](../consolidate/spec.md).

[NEEDS CLARIFICATION: The scope decision was flagged for separate discussion (G-6 in the original review). Re-examine whether the conservative scope is right once we've seen actual cross-cluster findings on the real corpus.]

## Approach

### 4.5a · Embedding pre-filtering (deterministic)

- Collect all `ConsolidatedRequirement` records into a global pool.
- For each requirement, compute or reuse its embedding via the same wrapper used in [consolidate](../consolidate/spec.md) (the `grouping: ` prefix), cached on content hash.
- Compute pairwise cosine similarity across the entire pool, but **exclude same-cluster pairs** and pairs whose `cluster_distance < min_pair_cluster_distance` (default 1).
- Retain pairs with `similarity ≥ cross_cluster.embedding_threshold` (default 0.85).
- If the candidate count exceeds `cross_cluster.max_candidate_pairs` (default 500), halt with a warning rather than proceeding silently — the consultant decides whether to raise the threshold or raise the cap.
- Write `cross_cluster/candidates.json` with all surviving pairs.

### 4.5b · LLM verification

- For each candidate pair, call the `verify_cross_cluster_conflict` prompt with both consolidated requirements (statement, type, status, sources excerpts) and both cluster summaries as context.
- The LLM returns a structured `verdict: confirmed_conflict | not_a_conflict | needs_review`, the inferred `kind`, a description, and a rationale.
- `needs_review` is a deliberate third option for cases the LLM is uncertain about — surfaced for human judgment rather than forced into a binary.
- Cached on `hash(both consolidated_requirement_ids + both cluster_summary_hashes + prompt_version + model)`. Reusing two stable inputs means re-runs after consolidation changes only invalidate verifications that touch changed inputs.

### 4.5c · Emit

- Write `cross_cluster/conflicts.json` with all verified records (including `not_a_conflict` and `needs_review` for cache persistence).
- For each `confirmed_conflict` and `needs_review`, write/update the relevant `clusters/<cluster>/consolidated/cross_cluster_annotations.json` sidecars referencing the conflict id.
- Per-cluster `requirements.json` is NOT modified — annotations live in sidecars to preserve immutability ([D-42]).

### 4.5d · Review queue regeneration

- Top-level `review_queue.json` is regenerated to fold in cross-cluster annotations.
- For each `ReviewQueueItem` whose `consolidated_requirement_id` appears in any `confirmed_conflict`, apply `cross_cluster_boost` to `review_priority` (default 0.20).
- The `cross_cluster_conflicts` field on the item lists the relevant conflict ids; `tags` gains `cross_cluster_conflict`.
- `review_priority_components` breaks down the additive contributions so the boost is auditable.

## Configuration (in `config/consolidation.yaml`)

```yaml
cross_cluster:
  enabled: true                      # set false to skip; or use --no-cross-cluster
  embedding_threshold: 0.85          # conservative; only highly-similar pairs get LLM verification
  detect_kinds: [contradiction, scope_mismatch]
  max_candidate_pairs: 500           # hard cap; if exceeded, halt and surface as a warning
  min_pair_cluster_distance: 1       # 1 = siblings or unrelated; 0 = same cluster (always excluded)
```

## Data shapes

### CrossClusterCandidate (`cross_cluster/candidates.json`)

Intermediate output of the embedding pre-filtering. Persisted for inspectability and cache reuse.

```json
{
  "candidate_id": "cc-cand-0042",
  "a": {
    "consolidated_requirement_id": "<cluster>:<index>",
    "cluster_path": "clusters/payments-service",
    "statement": "...",
    "type": "functional",
    "status": "implemented"
  },
  "b": {
    "consolidated_requirement_id": "<cluster>:<index>",
    "cluster_path": "clusters/checkout-experience",
    "statement": "...",
    "type": "functional",
    "status": "planned"
  },
  "similarity": 0.89,
  "cluster_distance": 2,
  "verified": false
}
```

### CrossClusterConflict (`cross_cluster/conflicts.json`)

Verified cross-cluster conflicts. Each entry references the two participating per-cluster `ConsolidatedRequirement` records but does not duplicate them.

```json
{
  "id": "cc-conf-0007",
  "candidate_id": "cc-cand-0042",
  "kind": "contradiction | scope_mismatch",
  "participants": [
    {"consolidated_requirement_id": "...", "cluster_path": "..."},
    {"consolidated_requirement_id": "...", "cluster_path": "..."}
  ],
  "description": "Cluster A says system MUST X; cluster B says system MUST NOT X for the same flow.",
  "evidence": [
    {"consolidated_requirement_id": "...", "excerpt": "<verbatim from source>"},
    {"consolidated_requirement_id": "...", "excerpt": "<verbatim from source>"}
  ],
  "verdict": "confirmed_conflict",
  "verdict_rationale": "<one-paragraph LLM explanation>",
  "detected_by": {
    "model": "<pinned reasoning model>",
    "prompt_version": "<hash>"
  }
}
```

This stage emits one record per LLM-verified candidate. `verdict: not_a_conflict` entries are kept (not deleted) so re-runs don't re-pay for verifying the same negative cases.

### CrossClusterAnnotation (`clusters/<cluster>/consolidated/cross_cluster_annotations.json`)

Sidecar file that links per-cluster `ConsolidatedRequirement` records to their cross-cluster conflict participations. **Preserves immutability of per-cluster outputs:** `requirements.json` is not modified. Downstream consumers (review queue generation, report) read both files together.

```json
{
  "annotations": [
    {
      "consolidated_requirement_id": "<cluster>:<index>",
      "cross_cluster_conflicts": ["cc-conf-0007", "cc-conf-0012"]
    }
  ],
  "generated_by": {
    "stage": "cross_cluster_reconciliation",
    "version": "<config/consolidation.yaml version>",
    "generated_at": "<ISO timestamp>"
  }
}
```

## Directory layout

```
cross_cluster/
├── candidates.json           # candidate pairs after embedding pre-filtering
└── conflicts.json            # verified cross-cluster conflicts
```

Per-cluster sidecar: `clusters/<cluster>/consolidated/cross_cluster_annotations.json`.

## Related decisions

- [D-40](../../decisions/0040-cross-cluster-as-separate-stage.md) separate stage with priority boost.
- [D-41](../../decisions/0041-cross-cluster-conservative-scope.md) conservative scope (flagged for re-examination).
- [D-42](../../decisions/0042-annotations-as-sidecar-files.md) sidecar annotations preserve immutability.
- [D-43](../../decisions/0043-cross-cluster-always-runs.md) always runs by default; config-gated.
- [D-44](../../decisions/0044-hard-candidate-cap-halt-warn.md) hard candidate cap.

## Related risks

- [R-2](../../risks.md) targeted, not exhaustive.
- [R-21](../../risks.md) candidate explosion.
- [R-22](../../risks.md) verification false negatives are invisible.
- [R-23](../../risks.md) boost may distort low-criticality priority.

## Failure modes

- **Candidate explosion.** A corpus with many similar-but-legitimately-distinct requirements can produce thousands of candidates. Mitigation: hard cap halts with a warning; the consultant raises the threshold or accepts a larger cap explicitly.
- **LLM verification false positives.** The verifier confirms a "conflict" that the per-cluster contexts make irrelevant. Mitigation: cluster summaries are part of the prompt; `needs_review` is a first-class verdict.
- **LLM verification false negatives.** The verifier rejects a real conflict (e.g., subtle scope mismatch). Mitigation: borderline cases that score in a `verdict: needs_review` band are surfaced; the consultant can override via the same `consolidation_overrides/` mechanism extended to cross-cluster ids.
- **Cluster reorganization invalidates cached verifications.** If a cluster splits or merges, consolidated requirement ids change, and verification cache entries are orphaned. Mitigation: cache keys include consolidated requirement ids (which are content-derived); orphan entries naturally stop being read. Cache cleanup is opportunistic.
- **Annotation sidecars go stale.** If consolidate re-runs and produces different consolidated requirements (different ids), this stage's annotations may reference ids that no longer exist. Mitigation: this stage invalidates and rewrites annotation sidecars based on the current consolidate output; orphaned annotations are detected on read and ignored with a warning.
