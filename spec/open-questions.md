# Open questions and deferred items

What's not in v1, why, and what would trigger revisiting it. Each entry has the same shape:

> **Title.** What's the question or deferred item.
>
> **Why it matters.** What's at stake.
>
> **What would resolve it.** Concrete trigger or next step.
>
> **Deferred for.** Reason it's not in v1.

This is also where reviewer-flagged concerns and the consultant's larger-scale ideas live until they get their own change folder.

---

## Generic primitives

### Q-1 · `source_type` as directory key vs. enum

**Why it matters.** Today `source_type` is an enum spread across adapters, frontmatter, eval config, source-authority weights, and prompts. In most of those places it functions as "name of the directory the artifact came from." Replacing the enum with a directory-name + adapter-registry convention would simplify adding new source types and remove residual coupling.

**What would resolve it.** A change folder that introduces an adapter registry and replaces `source_type` lookups with adapter-name lookups. Per-source config (authority weight, default `evidence_strength`, default `normalization_kind`) co-located with each adapter.

**Deferred for.** PoC scope; the current enum is workable for the five known source types.

### Q-2 · Projection primitive

**Why it matters.** Git is currently special-cased ([D-22](decisions/0022-git-repo-curated-summary.md)) as the only source type that produces an LLM-curated summary. Cross-functional documents (RFPs, spreadsheets) that touch multiple subsystems are currently normalized as single docs, which is wrong for clustering. Very large evidence (monolith repos, in future engagements) would benefit from multiple projections (architecture summary, API surface, domain glossary).

**Direction.** A general **projection** primitive: a named (deterministic-or-LLM) function from an evidence artifact to one or more derived normalized docs, preserving provenance back to the source. Git's curated summary becomes a projection. Splitting an RFP into per-section partials becomes a projection. Multiple projections per evidence is supported via `projection: <name>` and `parent_evidence: <id>` in frontmatter.

**What would resolve it.** A focused change folder that introduces the projection primitive, retrofits the git adapter onto it, and adds one cross-functional adapter (RFP partials are the obvious first candidate).

**Deferred for.** Needs design discussion. Listed as the highest-leverage next change after this restructure lands. See [Q-3](#q-3--source-declared-intent), [Q-9](#q-9--client-estimation-report-ingestion), and [Q-10](#q-10--monolith-handling-via-projections).

### Q-3 · Source-declared intent

**Why it matters.** The extractor currently infers `status` (implemented / planned / proposed / abandoned) per requirement from source-type cues. But "this evidence describes intended state, not built state" is really a property of *the evidence*, not of each requirement in it. Without a way to declare this, ingesting the client's pre-existing estimation report (see [Q-9](#q-9--client-estimation-report-ingestion)) would produce false `status_disagreement` conflicts every time the code doesn't yet match.

**Direction.** A projection (or evidence record) declares an `intent: implemented | planned | proposed | mixed` and a `default_status`. Requirements inherit unless the extractor has strong contrary evidence. Cross-status comparisons that would normally produce a `status_disagreement` are suppressed when the difference is explained by the sources' declared intents.

**What would resolve it.** The same change folder that introduces projections is the natural home.

**Deferred for.** Couples with [Q-2](#q-2--projection-primitive).

---

## Clustering

### Q-4 · Pure embedding-based clustering is not trustworthy enough

**Why it matters.** Stage 3a relies on embeddings for cluster assignment. The consultant has flagged that this is not trustworthy enough on its own; for sources with strong structured signal (Jira components, repo names, RFP section headers), embeddings are the weakest of the available signals.

**Direction.** Reframe clustering as **candidate reduction → LLM final assignment**: structured pre-grouping where available, embedding similarity as a fallback ranker, LLM final assignment for the top-K candidates per doc.

**What would resolve it.** A change folder dedicated to this rework. Likely depends on the projection primitive being in place first, because clustering candidate-reduction will want to use projections.

**Deferred for.** Bigger conceptual change; needs design discussion.

### Q-5 · Taxonomy discovery should feed clustering

**Why it matters.** Discovery already samples docs and learns about structure. Its findings (e.g., "this Jira project consistently tags by component X") could feed clustering candidate reduction directly. Currently discovery output is consumed only by extractors.

**Direction.** Discovery emits, in addition to taxonomy values, **clustering hints** per source type (component/repo mappings, header-to-cluster heuristics, naming conventions). These are persisted alongside the locked taxonomy and consumed by clustering.

**What would resolve it.** Part of the clustering rework ([Q-4](#q-4--pure-embedding-based-clustering-is-not-trustworthy-enough)).

**Deferred for.** Couples with Q-4.

---

## Conflict handling

### Q-6 · Top-N priority should include subsystem centrality and resolution uncertainty

**Why it matters.** The current `review_priority` formula is per-item: `criticality_numeric * (1 - confidence)`. At top-level rendering it doesn't account for how central the cluster (subsystem) is to the whole system, nor for how uncertain the auto-resolution of a conflict was.

**Direction.** Extend the formula at top-level rendering with two factors:

- **Subsystem centrality.** A per-cluster scalar derived from cluster size, inbound-interaction count, and (optionally) explicit consultant marking. Computed deterministically.
- **Resolution uncertainty.** A scalar derived from which reconciliation rule fired and what its evidence looked like. `manual_override` → 0. `source_authority` with tied weights → high. `llm_judgment` → high.

Within-cluster ordering keeps the simple formula.

**What would resolve it.** A change folder that adds these two factors and updates the report rendering. Cheap to implement; can land any time after the consolidate spec is in code.

**Deferred for.** Phase 1 ships with the simple formula; the consultant accepts the noise.

### Q-7 · Conflict feedback loop with the client

**Why it matters.** Top-N conflicts become client questions, the client answers, and the system needs to fold that feedback in and surface the next top-N. The pipeline today produces a static review queue.

**Direction.** Treat client answers as evidence (a new source type or a dedicated `answers/` directory with its own adapter) with high authority. Each conflict gains a lifecycle state (`open | answered | superseded | closed`). A `conflict:resolve <id>` operation accepts feedback, writes it as evidence, re-runs the affected portions of consolidation, and regenerates `review_queue.json`.

**What would resolve it.** A change folder. The underlying mechanics are mostly in place; what's missing is naming the operation and tracking state.

**Deferred for.** Comes after the basic pipeline is producing review queues on the real corpus, so the conflict shapes are known.

---

## Eval and calibration (deferred wholesale)

### Q-8 · Eval framework

**Why it matters.** Without automated regression detection, prompt edits can silently degrade extraction quality. The v0 spec designed a full framework (per-extractor styles, judge prompts, eval cache, run records).

**Direction.** Re-introduce when the pipeline shape is stable and the consultant has the discipline budget. Likely as a parallel concern that doesn't gate pipeline execution, with a `report` health-section signal for staleness.

**What would resolve it.** A change folder once the pipeline is no longer in heavy iteration.

**Deferred for.** Phase 1 is proof-of-concept. The consultant accepts LLM-generated prompts with manual spot-checks. Reintroducing the eval framework would add significant complexity for marginal protection during PoC iteration.

### Q-9a · Calibration framework

**Why it matters.** Default confidence weights are guesses. Without calibration, the review queue ordering is a starting point, not a ranked answer.

**Direction.** Re-introduce when the pipeline is producing review queues on a real corpus and the consultant has time to author calibration cases.

**What would resolve it.** A change folder that re-introduces the calibration loop (`CalibrationCase`, `CalibrationRun`, `tuned_weights.yaml`, `calibrate:run` and `calibrate:accept` commands).

**Deferred for.** The consultant has confirmed they will not author calibration cases in v1.

---

## New requirements not yet specified

### Q-9b · Client estimation report ingestion

**Why it matters.** The consultant will receive a client-authored estimation report describing planned productization work, with the client's own work estimates. This needs to be ingested, travel through clustering/extraction/consolidation, and be **compared** to our findings (the whole point is to validate the client's estimates). Without source-declared intent (Q-3), this would produce false status-disagreement conflicts against implemented code.

**Direction.** Once projections ([Q-2](#q-2--projection-primitive)) and intent declaration ([Q-3](#q-3--source-declared-intent)) are in place, this is mostly automatic. Remaining work is a **validation view**: a report section (or separate report) that pairs each client-estimated work item with our findings for the same cluster/concept and flags discrepancies.

**What would resolve it.** A change folder that adds the validation view, after [Q-2](#q-2--projection-primitive) and [Q-3](#q-3--source-declared-intent) land.

**Deferred for.** Depends on Q-2 and Q-3.

### Q-10 · Monolith handling via projections

**Why it matters.** Current scope (35 microservices, 500 KLOC) makes "one repo = one cluster seed" reasonable. For future engagements with monoliths, modules within the monolith would need to be identified first and projected separately.

**Direction.** Reuse the projection primitive ([Q-2](#q-2--projection-primitive)). A monolith adapter emits one projection per identified module. No new mechanism needed.

**What would resolve it.** Encountering a monolith.

**Deferred for.** Not relevant to the current engagement.

### Q-11 · Transformation-estimate framing

**Why it matters.** The pipeline is meticulous about producing a high-quality review queue but doesn't show the line from queue to the actual consultant deliverable (transformation scale estimate + Gen-AI acceleration assessment). The reviewer flagged this; the consultant agreed it deserves its own short design.

**Direction (sketch).**

- **Coverage per cluster.** For each cluster, count requirements by `change_plan_flag` (work to do) vs. implemented. Multiply by cluster centrality (from [Q-6](#q-6--top-n-priority-should-include-subsystem-centrality-and-resolution-uncertainty)). Rough effort signal.
- **Validation against client estimate** (from Q-9b). Where do we agree on scope? Where does our scope exceed theirs? Per cluster.
- **Gen-AI acceleration heuristic.** Per cluster, score along axes the consultant cares about (boilerplate-heavy, well-documented, type-safe domain model, integration-heavy, regulated, etc.). Heuristics, not LLM judgments.

**What would resolve it.** A focused design discussion once the pipeline is producing review queues. Probably a thin downstream layer rather than a pipeline stage.

**Deferred for.** Out of scope for the pipeline spec; in scope for a thin downstream layer to be designed after first runs.

---

## Specific decision flagged for re-examination

### Q-12 · Cross-cluster scope ([D-41](decisions/0041-cross-cluster-conservative-scope.md)) — re-examine after first real run

**Why it matters.** The conservative scope excludes three of the five conflict kinds from cross-cluster detection. "What part of the change plan crosses subsystem boundaries?" is a question the assessment is trying to answer, and the exclusions might hide signal there.

**What would resolve it.** First real run on the corpus produces actual cross-cluster findings. If the consultant finds the conservative scope is leaving important conflicts uncaught, a change folder revisits [D-41](decisions/0041-cross-cluster-conservative-scope.md).

**Deferred for.** Empirical: need data from the first run.

---

## Items dropped from v1 spec with no current trigger

- **Cluster archival** ([D-49] through [D-52] in v0). Not needed in the PoC timeframe. Re-introduce if the pipeline runs long enough to accumulate stale clusters.
- **Hierarchical super-clustering** ([cluster-hierarchy](specs/cluster-hierarchy/spec.md)) is **kept** in v1 per consultant request, but flagged as experimental — see the spec for `[NEEDS CLARIFICATION]` markers around proposal/apply workflow.
