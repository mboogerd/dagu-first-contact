# Consolidate (Stage 4)

Group extracted requirements per domain, surface and resolve conflicts with explicit kinds, detect cross-domain conflicts during bottom-up traversal, and score for human review priority. Produce a ranked review queue.

**Phase.** Stage 4.

**Input → Output.** `domains/` + `extracted/` + `config/consolidation.yaml` → `domains/**/<domain-name>__groups/` + `domains/**/<domain-name>__review-queue.md` + `domains/root__review-queue.md`.

---

## Approach

Runs **bottom-up** through the domain tree. At each domain, seven phases execute in sequence; child-domain outputs propagate upward as inputs.

### 4a · Gather

- For each domain, collect all `Requirement` records from member docs (via `extracted/<source_type>/<source_id>/requirements.json`).
- Collect already-consolidated requirements from child domains (each propagates upward as a single record carrying its own `sources` and `conflicts`).

### 4b · Group (two-stage)

**Pre-grouping (deterministic):**

- Each requirement gets an embedding via the [embedding wrapper](../embedding/spec.md), with the `clustering: ` prefix replaced by a `grouping: ` prefix (recorded in the embedding sidecar). Embeddings are content-hash cached.
- Compute pairwise cosine similarity within the domain's requirement set; build candidate groups as connected components where every edge >= `grouping.embedding_threshold` (default 0.78).
- Singletons (requirements with no above-threshold neighbors) become singleton candidates.

**LLM verification:**

- For each multi-member candidate group, call the `group_requirements` prompt with the member statements and source metadata. The LLM returns one of: `confirm`, `split` (with proposed sub-grouping), `reject` (members are unrelated).
- `split` produces multiple output groups; `reject` dissolves to singletons.
- Verification call cached on `hash(sorted(member_content_hashes) + prompt_version + model)`.
- `config/consolidation.yaml: grouping.llm_verification: false` is an escape hatch that skips verification and uses pre-groups directly (useful for cost-bounded re-runs; recorded in group provenance).

Output: per-`RequirementGroup` markdown files under `domains/<path>/<domain-name>__groups/`.

### 4c · Conflict detection

Per group, detect all applicable conflict kinds:

**Deterministic detections** (cheap, run first):

- `status_disagreement`: members have >=2 distinct `status` values. **Suppressed** when the difference is explained by participants' projections' intents (e.g., one source has `intent: planned` and `status: planned`, another has `intent: implemented` and `status: implemented` — this is expected, not a conflict).
- `type_disagreement`: members have >=2 distinct `type` values.
- `version_skew` (candidate): `source_date` spread exceeds a threshold (default 180 days) AND members have non-trivial statement variation.

**LLM-driven detections** (called only when the group has >=2 members):

- `contradiction`: explicit negation or mutual exclusivity between statements.
- `scope_mismatch`: agreement on behavior with disagreement on scope/applicability.
- Confirms or rejects candidate `version_skew` cases.

A group can have multiple conflicts of different kinds. Each conflict carries explicit `evidence` (the contributing requirements with verbatim excerpts). LLM-driven detection is a single call per group with a structured-output schema enumerating all conflict kinds found; cached on group inputs.

**Intent-based suppression rule:** suppress `status_disagreement` when the set of source `intent` values is `{implemented, planned}` or `{implemented, proposed}` or `{planned, proposed}` and the resolved statuses align with those intents. See [D-50].

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

- Call the `assess_criticality` prompt with the resolved statement and the domain's summary as context.
- The LLM emits one of `critical | important | moderate | minor` (the fixed scale) plus a one-sentence rationale.
- The numeric value is looked up from `config/consolidation.yaml: criticality.numeric`; the LLM does not emit floats.
- Cached on `hash(statement + domain_summary_hash + prompt_version + model)`.

**Review priority (deterministic).**

- Computed from the formula in `config/consolidation.yaml: review_priority.formula`. Default: `criticality_numeric * (1 - confidence.score)` + optional `change_plan_boost`.
- The combination favors items that are both critical AND uncertain — exactly the cases worth a human's time.

### 4f · Cross-domain findings (at non-leaf domains)

At each non-leaf domain, after gathering children's consolidated outputs, an additional pass detects `contradiction` and `scope_mismatch` conflicts **between the children's consolidations**:

- For each pair of child domains, compare their consolidated requirements using the same embedding pre-filtering and LLM verification as within-domain conflict detection.
- Findings land in the **lowest common ancestor** domain's folder as `<domain-name>__cross-domain-findings.md`.
- For findings whose participants don't share a non-root ancestor, findings land at `domains/root__cross-domain-findings.md` (the root is materialized as a real domain).
- Cross-domain findings carry a `cross_domain_boost` (default 0.20) applied to the participating items' review priority.
- The boost is a domain-local concept: applied when a parent's review queue rolls up child queues, weighted by where the finding sits in the tree.

Scope: only `contradiction` and `scope_mismatch`. `status_disagreement`, `type_disagreement`, and `version_skew` are excluded because same-named concepts in different domains legitimately differ on these dimensions.

### 4g · Emit

- Write per-`RequirementGroup` markdown files under `domains/<path>/<domain-name>__groups/<domain-name>__group-NNNN.md`. Each requirement within a group is a `##` section with a stable heading ID like `req-PROJ-123-0` so block references work: `[[<domain-name>__group-NNNN#req-PROJ-123-0]]`.
- Group frontmatter carries the group's resolved type/status/criticality/confidence and conflict summary.
- Write `<domain-name>__review-queue.md` as a markdown table, with rows linked via wikilink to the group sections. One per domain; recursive roll-up — a parent's review queue absorbs its children's, weighted by child-domain centrality.
- Write cross-domain findings markdown at non-leaf domains.
- The top-level review queue lives at `domains/root__review-queue.md`. No separate top-level `reviewqueue.json`.
- Propagate `ConsolidatedRequirement` records upward; the parent domain's `gather` will treat each as a single source.

## Caching

Consolidation is cached at three levels:

- **Group-level:** grouping result cached on member content hashes + grouping config.
- **Conflict-level:** conflict detection cached on group inputs.
- **Criticality-level:** criticality cached on statement + domain summary hash.

Re-running consolidation when nothing has changed is near-free; changing `config/consolidation.yaml` invalidates the relevant levels selectively. See [D-38].

## Configuration (`config/consolidation.yaml`)

```yaml
version: "<semver or hash>"

grouping:
  embedding_threshold: 0.78        # cosine; candidates above this enter LLM verification
  llm_verification: true           # set false to use pure embedding grouping (escape hatch)
  min_group_size: 1                # singletons (one source) are valid groups

source_authority:
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
  cross_domain_boost: 0.20

cross_domain:
  embedding_threshold: 0.85
  detect_kinds: [contradiction, scope_mismatch]
  max_candidate_pairs: 500
```

## Data shapes

### RequirementGroup markdown (`domains/<path>/<domain-name>__groups/<domain-name>__group-NNNN.md`)

```yaml
---
group_id: "<domain>:NNNN"
domain_path: "domains/financial-domain/payments-service"
type: functional
status: implemented
criticality: important
criticality_rationale: "Core payment processing is central to the domain's purpose."
confidence: 0.62
change_plan_flag: false
conflicts:
  - kind: status_disagreement
    description: "Sources disagree on implementation status."
review_priority: 0.42
---

## req-PROJ-123-0

**Statement.** The system must process refunds within 24 hours.

**Source.** `jira` / `PROJ-123` / 2026-02-14
**Excerpt.** > "Refund processing must complete within 24 hours of approval"
**Type.** functional | **Status.** implemented

---

## req-rfp-doc-12-3

**Statement.** Refund processing shall not exceed one business day.

**Source.** `rfp` / `doc-12` / 2026-01-10
**Excerpt.** > "All refund operations shall complete within one business day"
**Type.** functional | **Status.** proposed
```

Each requirement within a group has a stable `## req-<source-id>-<index>` heading so wikilinks resolve: `[[payments-service__group-0001#req-PROJ-123-0]]`.

### Review queue markdown (`domains/<path>/<domain-name>__review-queue.md`)

A markdown table with rows linked to group sections:

```markdown
# payments-service — Review Queue

| # | Priority | Statement | Type | Criticality | Confidence | Conflicts | Group |
|---|----------|-----------|------|-------------|------------|-----------|-------|
| 1 | 0.62 | The system must process refunds... | functional | important | 0.62 | status_disagreement | [[payments-service__group-0001]] |
| 2 | 0.45 | ... | ... | ... | ... | ... | [[payments-service__group-0002]] |
```

Parent domain review queues recursively absorb their children's queues, weighted by child-domain centrality.

### Cross-domain findings (`domains/<path>/<domain-name>__cross-domain-findings.md`)

```markdown
# financial-domain — Cross-Domain Findings

## Finding 1: contradiction between payments-service and checkout-experience

**Kind.** contradiction
**Participants.**
- [[payments-service__group-0042#req-PROJ-456-0]]: "System MUST enforce 3DS for all transactions"
- [[checkout-experience__group-0017#req-rfp-doc-12-5]]: "3DS is optional for transactions under EUR 30"

**Description.** Direct contradiction on 3DS enforcement scope.
**Rationale.** <LLM explanation>
```

### Tags

Tags are derived flags surfaced in the review queue for filtering:

- `change_plan` — `change_plan_flag` is true.
- `<conflict_kind>` — one tag per distinct `conflict.kind` present.
- `low_confidence` — `confidence.score < 0.4`.
- `borderline_criticality` — criticality is within the borderline band.
- `singleton` — group has exactly one source.
- `cross_domain_finding` — item participates in at least one cross-domain finding.

## Related decisions

- [D-10](../../decisions/0010-provenance-driven-conflict-resolution.md) provenance-driven resolution.
- [D-11](../../decisions/0011-bottom-up-consolidation.md) bottom-up.
- [D-13](../../decisions/0013-expensive-model-at-consolidation-only.md) expensive model here.
- [D-34](../../decisions/0034-two-stage-requirement-grouping.md) two-stage grouping.
- [D-35](../../decisions/0035-explicit-conflict-kinds.md) explicit conflict kinds.
- [D-36](../../decisions/0036-deterministic-confidence.md) deterministic confidence.
- [D-37](../../decisions/0037-discrete-criticality-scale.md) discrete criticality scale.
- [D-38](../../decisions/0038-layered-consolidation-caching.md) layered caching.
- [D-50](../../decisions/0050-source-declared-intent.md) source-declared intent (status_disagreement suppression).

## Related risks

- [R-5](../../risks.md) confidence/criticality is uncalibrated in v1.
- [R-6](../../risks.md) source-authority weights are guesses.
- [R-18](../../risks.md) grouping is the longest-lever single failure.
- [R-20](../../risks.md) manual reconciliation overrides go stale.

## Failure modes

- **Cross-domain conflicts limited to parent-child views.** The bottom-up traversal detects conflicts between sibling domains at each tree level; conflicts between distant branches (cousins) that don't share an immediate parent only surface at the root. Acceptable: the root's cross-domain findings catch these.
- **Grouping over-merges.** Embedding pre-grouping followed by LLM `confirm` can still merge requirements that share vocabulary but differ in scope. Mitigation: LLM verification's `split` outcome is the primary defense; `scope_mismatch` conflict detection catches surviving cases.
- **Grouping under-merges.** Paraphrased equivalents fall below the embedding threshold and never enter LLM verification. Partial mitigation: threshold defaults at 0.78 are conservative; lowering increases LLM verification cost but improves recall.
- **Criticality miscalibration on niche domains.** A domain with very narrow scope may have its critical items rated `moderate` because the LLM lacks domain context. Mitigation: `assess_criticality` prompt anchors to the domain summary.
- **Confidence weights mis-tuned.** Default weights are guesses. Accepted in v1.
- **Manual overrides go stale.** An override authored in iteration 3 may no longer match the resolved group in iteration 12 (membership changed). Mitigation: overrides are keyed on `group_id`, which is content-derived; when the group changes, the override stops matching and a warning is emitted.
- **Candidate explosion in cross-domain pass.** A corpus with many similar requirements across domains can produce thousands of candidate pairs. Mitigation: hard cap (`max_candidate_pairs`); the stage halts with a warning if exceeded.
