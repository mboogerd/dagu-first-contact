# Consolidate (Stage 4)

Group extracted requirements per cluster, surface and resolve conflicts with explicit kinds, and score for human review priority. Produce a ranked review queue.

**Phase.** Stage 4.

**Input → Output.** `clusters/` + `extracted/` + `config/consolidation.yaml` → `clusters/**/consolidated/` + `review_queue.json`.

---

## Approach

Runs **bottom-up** through the cluster tree. At each cluster, six phases execute in sequence; child-cluster outputs propagate upward as inputs.

### 4a · Gather

- For each cluster, collect all `Requirement` records from member docs (via `extracted/<source_type>/<source_id>/requirements.json`).
- Collect already-consolidated requirements from child clusters (each propagates upward as a single record carrying its own `sources` and `conflicts`).

### 4b · Group (two-stage)

**Pre-grouping (deterministic):**

- Each requirement gets an embedding via the [embedding wrapper](../embedding/spec.md), with the `clustering: ` prefix replaced by a `grouping: ` prefix (recorded in the embedding sidecar). Embeddings are content-hash cached.
- Compute pairwise cosine similarity within the cluster's requirement set; build candidate groups as connected components where every edge ≥ `grouping.embedding_threshold` (default 0.78).
- Singletons (requirements with no above-threshold neighbors) become singleton candidates.

**LLM verification:**

- For each multi-member candidate group, call the `group_requirements` prompt with the member statements and source metadata. The LLM returns one of: `confirm`, `split` (with proposed sub-grouping), `reject` (members are unrelated).
- `split` produces multiple output groups; `reject` dissolves to singletons.
- Verification call cached on `hash(sorted(member_content_hashes) + prompt_version + model)`.
- `config/consolidation.yaml: grouping.llm_verification: false` is an escape hatch that skips verification and uses pre-groups directly (useful for cost-bounded re-runs; recorded in group provenance).

Output: `clusters/<cluster>/consolidated/groups.json` with one `RequirementGroup` record per group.

### 4c · Conflict detection

Per group, detect all applicable conflict kinds:

**Deterministic detections** (cheap, run first):

- `status_disagreement`: members have ≥2 distinct `status` values.
- `type_disagreement`: members have ≥2 distinct `type` values.
- `version_skew` (candidate): `source_date` spread exceeds a threshold (default 180 days) AND members have non-trivial statement variation.

**LLM-driven detections** (called only when the group has ≥2 members):

- `contradiction`: explicit negation or mutual exclusivity between statements.
- `scope_mismatch`: agreement on behavior with disagreement on scope/applicability.
- Confirms or rejects candidate `version_skew` cases.

A group can have multiple conflicts of different kinds. Each conflict carries explicit `evidence` (the contributing requirements with verbatim excerpts). LLM-driven detection is a single call per group with a structured-output schema enumerating all conflict kinds found; cached on group inputs.

### 4d · Reconciliation

For each group, produce the resolved `statement`, `type`, and `status`:

- Apply reconciliation rules in the order defined in `config/consolidation.yaml: reconciliation.rules`.
- `manual_override`: looks up `config/consolidation_overrides/<group_id>.yaml` if present; if so, the override's values are used and `applied_rule: manual_override` is recorded.
- `source_authority`: sources are weighted by `source_authority`; the highest-weighted source's values win. Ties fall through.
- `recency`: most recent `source_date` wins. Ties fall through.
- `llm_judgment`: final fallback. Single LLM call with the `reconcile_group` prompt, returning the resolved values and a rationale. Always records rationale via `Conflict.resolution.rationale`.

When the resolved `statement` is a synthesis (i.e., not verbatim from any single source), this is flagged in the resolution rationale and the synthesis is recorded as the `statement` while the original excerpts remain in `sources`.

### 4e · Scoring

**Confidence (deterministic).** Compute the five signals:

- `source_count` (log-scaled): `min(1.0, log(1 + n) / log(1 + 5))` — saturates around 5 sources.
- `authority_weighted_agreement`: weighted fraction of sources whose statement/type/status matches the resolved values, weighted by `source_authority`.
- `recency_spread_penalty`: `min(1.0, spread_days / 730)` — penalty saturates at 2 years.
- `statement_similarity`: mean pairwise cosine similarity of member statements (from grouping embeddings; effectively free).
- `conflict_penalty`: 1.0 if any `Conflict` is present, else 0.0.

Combine via the weighted formula in `config/consolidation.yaml: confidence.weights`:

```
score = w_count * source_count
      + w_auth * authority_weighted_agreement
      + w_sim * statement_similarity
      - w_recency * recency_spread_penalty
      - w_conflict * conflict_penalty
```

Clamped to [0, 1]. Signals and weights are recorded in the `Confidence` object for full auditability.

**Weights in v1 are defaults; calibration is deferred.** See [open-questions.md](../../open-questions.md).

**Criticality (LLM, cached).**

- Call the `assess_criticality` prompt with the resolved statement and the cluster's `summary.md` as context.
- The LLM emits one of `critical | important | moderate | minor` (the fixed scale) plus a one-sentence rationale.
- The numeric value is looked up from `config/consolidation.yaml: criticality.numeric`; the LLM does not emit floats.
- Cached on `hash(statement + cluster_summary_hash + prompt_version + model)`.

**Review priority (deterministic).**

- Computed from the formula in `config/consolidation.yaml: review_priority.formula`. Default: `criticality_numeric * (1 - confidence.score)` + optional `change_plan_boost`.
- The combination favors items that are both critical AND uncertain — exactly the cases worth a human's time.

### 4f · Emit

- Write `clusters/<cluster>/consolidated/requirements.json` (list of `ConsolidatedRequirement`).
- Write `clusters/<cluster>/consolidated/review_queue.json` (cluster-local queue, sorted by `review_priority`).
- Propagate `ConsolidatedRequirement` records upward; the parent cluster's `gather` will treat each as a single source.

After all clusters: merge all cluster-local queues into top-level `review_queue.json`, sorted by `review_priority` descending, with `tags` derived (see below).

## Caching

Consolidation is cached at three levels:

- **Group-level:** grouping result cached on member content hashes + grouping config.
- **Conflict-level:** conflict detection cached on group inputs.
- **Criticality-level:** criticality cached on statement + cluster summary hash.

Re-running consolidation when nothing has changed is near-free; changing `config/consolidation.yaml` invalidates the relevant levels selectively. See [D-38].

## Configuration (`config/consolidation.yaml`)

```yaml
version: "<semver or hash>"

grouping:
  embedding_threshold: 0.78        # cosine; candidates above this enter LLM verification
  llm_verification: true           # set false to use pure embedding grouping (escape hatch)
  min_group_size: 1                # singletons (one source) are valid groups

source_authority:
  # Used in reconciliation tie-breaking and in confidence's authority-weighted-agreement signal.
  # Values are unitless weights; only relative magnitude matters.
  rfp: 1.0
  spreadsheet: 0.7
  jira: 0.6
  git: 0.8
  transcript: 0.4

reconciliation:
  rules:
    - manual_override
    - source_authority
    - recency
    - llm_judgment

confidence:
  weights:
    source_count: 0.20
    authority_weighted_agreement: 0.35
    recency_spread_penalty: 0.10
    statement_similarity: 0.15
    conflict_penalty: 0.20

criticality:
  scale: [critical, important, moderate, minor]
  numeric:
    critical: 1.00
    important: 0.70
    moderate: 0.40
    minor: 0.15

review_priority:
  formula: "criticality_numeric * (1 - confidence)"
  change_plan_boost: 0.0
  cross_cluster_boost: 0.20        # applied by cross-cluster stage; see ../cross-cluster/spec.md
```

## Data shapes

### RequirementGroup (`clusters/<cluster>/consolidated/groups.json`)

```json
{
  "group_id": "<cluster>:<index>",
  "cluster_path": "clusters/financial-domain/payments-service",
  "members": [
    {
      "requirement_id": "<from extracted/.../requirements.json>",
      "source_id": "...",
      "source_type": "jira",
      "source_date": "2026-02-14",
      "statement": "...",
      "type": "functional",
      "status": "planned"
    }
  ],
  "grouping": {
    "embedding_similarity_min": 0.81,
    "embedding_similarity_mean": 0.86,
    "llm_verified": true,
    "llm_verdict": "confirm | split | reject",
    "llm_split_reason": null,
    "verification_model": "<pinned id>",
    "verification_prompt_version": "<hash>"
  }
}
```

### Conflict (embedded in `ConsolidatedRequirement.conflicts[]`)

A group can have zero or more conflicts. Conflicts have explicit kinds.

```json
{
  "kind": "contradiction | scope_mismatch | status_disagreement | version_skew | type_disagreement",
  "description": "<short human-readable summary>",
  "evidence": [
    {"requirement_id": "...", "excerpt": "<verbatim>", "stance": "must support X"},
    {"requirement_id": "...", "excerpt": "<verbatim>", "stance": "must not support X"}
  ],
  "detected_by": "deterministic | llm | both",
  "resolution": {
    "applied_rule": "manual_override | source_authority | recency | llm_judgment",
    "rationale": "<human-readable explanation>",
    "rationale_by": {"model": "...", "prompt_version": "..."}
  }
}
```

### Confidence (embedded in `ConsolidatedRequirement.confidence`)

```json
{
  "score": 0.62,
  "signals": {
    "source_count": 4,
    "authority_weighted_agreement": 0.78,
    "recency_spread_days": 412,
    "recency_spread_penalty": 0.10,
    "statement_similarity": 0.74,
    "conflict_present": true,
    "conflict_penalty": 0.20
  },
  "weights_version": "<config/consolidation.yaml version>",
  "formula_version": "<config/consolidation.yaml version>"
}
```

Confidence is a **deterministic** function of `signals` and `weights`. The same inputs always produce the same score. The LLM is not consulted for the score itself; it is consulted only for the qualitative parts of `Conflict` (description, resolution rationale).

### Criticality (embedded in `ConsolidatedRequirement.criticality`)

```json
{
  "level": "critical | important | moderate | minor",
  "numeric": 0.70,
  "rationale": "<one-sentence explanation from the LLM>",
  "assessed_by": {
    "model": "<pinned reasoning model>",
    "prompt_version": "<hash>"
  }
}
```

### ConsolidatedRequirement (`clusters/<cluster>/consolidated/requirements.json`)

```json
{
  "id": "<cluster>:<index>",
  "group_id": "<RequirementGroup.group_id>",

  "statement": "<resolved canonical statement>",
  "type": "<resolved single value from the type taxonomy>",
  "status": "<resolved single value from the status taxonomy>",

  "sources": [
    {"requirement_id": "...", "source_id": "...", "source_type": "...",
     "source_date": "...", "excerpt": "<verbatim>"}
  ],

  "conflicts": [
    { "...": "<Conflict>" }
  ],
  "change_plan_flag": true,

  "confidence": { "...": "<Confidence>" },
  "criticality": { "...": "<Criticality>" },
  "review_priority": 0.42,

  "resolved_by": {
    "model": "<pinned reasoning model>",
    "prompt_version": "<hash>"
  }
}
```

Resolution rules:

- `statement` is the canonical resolved text. If a single source dominated (per reconciliation rules), it's that source's statement (verbatim or lightly normalized); if the LLM produced a synthesis, the synthesis text and its provenance are recorded under the relevant `Conflict.resolution`.
- `type` and `status` are **single resolved values**. Disagreement among sources surfaces in `conflicts[]` with kinds `type_disagreement` or `status_disagreement` — the resolved value is in the top-level fields; the disagreement remains visible.
- `change_plan_flag` is a derived convenience flag, true when any contributing requirement had `type: change_plan` OR `status: planned | proposed`. The review queue treats this flag as a tagging signal.

### ReviewQueueItem (`review_queue.json`)

A flat sortable list, sorted descending by `review_priority`. Same shape as `ConsolidatedRequirement` plus location and a short tag set for filtering. Cross-cluster conflicts and the `cross_cluster_boost` are folded in by [cross-cluster](../cross-cluster/spec.md) at queue-generation time.

```json
{
  "cluster_path": "clusters/financial-domain/payments-service",
  "tags": ["change_plan", "type_disagreement", "borderline_criticality", "cross_cluster_conflict"],
  "cross_cluster_conflicts": ["cc-conf-0007"],
  "review_priority_components": {
    "base": 0.42,
    "change_plan_boost": 0.00,
    "cross_cluster_boost": 0.20,
    "total": 0.62
  },
  "...": "<all ConsolidatedRequirement fields>"
}
```

**Tags** are derived flags useful for filtering the review queue without recomputing:

- `change_plan` — `change_plan_flag` is true.
- `<conflict_kind>` — one tag per distinct `conflict.kind` present.
- `low_confidence` — `confidence.score < 0.4`.
- `borderline_criticality` — criticality is within the borderline band defined in `config/consolidation.yaml`.
- `singleton` — group has exactly one source (no cross-source corroboration).
- `cross_cluster_conflict` — item participates in at least one verified `CrossClusterConflict`.

## Related decisions

- [D-10](../../decisions/0010-provenance-driven-conflict-resolution.md) provenance-driven resolution.
- [D-11](../../decisions/0011-bottom-up-consolidation.md) bottom-up.
- [D-13](../../decisions/0013-expensive-model-at-consolidation-only.md) expensive model here.
- [D-34](../../decisions/0034-two-stage-requirement-grouping.md) two-stage grouping.
- [D-35](../../decisions/0035-explicit-conflict-kinds.md) explicit conflict kinds.
- [D-36](../../decisions/0036-deterministic-confidence.md) deterministic confidence.
- [D-37](../../decisions/0037-discrete-criticality-scale.md) discrete criticality scale.
- [D-38](../../decisions/0038-layered-consolidation-caching.md) layered caching.

## Related risks

- [R-5](../../risks.md) confidence/criticality is uncalibrated in v1.
- [R-6](../../risks.md) source-authority weights are guesses.
- [R-18](../../risks.md) grouping is the longest-lever single failure.
- [R-20](../../risks.md) manual reconciliation overrides go stale.

## Failure modes

- **Cross-cluster conflicts missed at this stage.** Bottom-up consolidation only sees one subtree at a time; conflicts between distant branches are not detected here. [cross-cluster](../cross-cluster/spec.md) addresses this.
- **Grouping over-merges.** Embedding pre-grouping followed by LLM `confirm` can still merge requirements that share vocabulary but differ in scope. Mitigation: LLM verification's `split` outcome is the primary defense; `scope_mismatch` conflict detection catches surviving cases.
- **Grouping under-merges.** Paraphrased equivalents fall below the embedding threshold and never enter LLM verification. Partial mitigation: threshold defaults at 0.78 are conservative; lowering increases LLM verification cost but improves recall.
- **Criticality miscalibration on niche clusters.** A cluster with very narrow scope may have its critical items rated `moderate` because the LLM lacks domain context. Mitigation: `assess_criticality` prompt anchors to the cluster summary. (Calibration is deferred; see open questions.)
- **Confidence weights mis-tuned.** Default weights are guesses. Accepted in v1; the consultant interprets review-queue ordering as a starting point, not a ranked answer.
- **LLM-emitted criticality drift across model versions.** A model upgrade can shift the distribution of criticality levels. Mitigation: criticality cache key includes the model id.
- **Manual overrides go stale.** An override authored in iteration 3 may no longer match the resolved group in iteration 12 (membership changed). Mitigation: overrides are keyed on `group_id`, which is content-derived; when the group changes, the override stops matching and a warning is emitted.
