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

**What would resolve it.** A change folder that introduces an adapter registry and replaces `source_type` lookups with adapter-name lookups. Per-source config (authority weight, default `evidence_strength`) co-located with each adapter.

**Deferred for.** PoC scope; the current enum is workable for the five known source types. The projection registry pattern ([D-49](decisions/0049-projection-primitive.md)) is a precedent for an adapter registry.

### ~~Q-2 · Projection primitive~~ RESOLVED

**Resolved by** [D-49](decisions/0049-projection-primitive.md) and change folder [001-projection-primitive](changes/001-projection-primitive/proposal.md). The projection primitive is now part of the stable spec. `normalized/` is replaced by `projections/`. Six projections ship in v1.

### ~~Q-3 · Source-declared intent~~ RESOLVED

**Resolved by** [D-50](decisions/0050-source-declared-intent.md). Intent (`implemented | planned | proposed | mixed`) is declared per projection. `status_disagreement` suppression for intent-explained differences is part of the consolidate spec.

---

## Domain assignment (clustering)

### Q-4 · Pure embedding-based domain assignment is not trustworthy enough

**Why it matters.** Stage 3a relies on embeddings for domain assignment. The consultant has flagged that this is not trustworthy enough on its own; for sources with strong structured signal (Jira components, repo names, RFP section headers), embeddings are the weakest of the available signals.

**Direction.** Reframe domain assignment as **candidate reduction → LLM final assignment**: structured pre-grouping where available, embedding similarity as a fallback ranker, LLM final assignment for the top-K candidates per doc.

**What would resolve it.** A change folder dedicated to this rework. Likely depends on the projection primitive being in place first (now resolved), because candidate-reduction will want to use projections.

**Deferred for.** Bigger conceptual change; needs design discussion.

### Q-5 · Taxonomy discovery should feed domain assignment

**Why it matters.** Discovery already samples docs and learns about structure. Its findings (e.g., "this Jira project consistently tags by component X") could feed domain assignment candidate reduction directly. Currently discovery output is consumed only by extractors.

**Direction.** Discovery emits, in addition to taxonomy values, **clustering hints** per source type (component/repo mappings, header-to-domain heuristics, naming conventions). These are persisted alongside the locked taxonomy and consumed by domain assignment.

**What would resolve it.** Part of the domain assignment rework ([Q-4](#q-4--pure-embedding-based-domain-assignment-is-not-trustworthy-enough)).

**Deferred for.** Couples with Q-4.

---

## Conflict handling

### Q-6 · Top-N priority should include subsystem centrality and resolution uncertainty

**Why it matters.** The current `review_priority` formula is per-item: `criticality_numeric * (1 - confidence)`. At top-level rendering it doesn't account for how central the domain (subsystem) is to the whole system, nor for how uncertain the auto-resolution of a conflict was.

**Direction.** Extend the formula at top-level rendering with two factors:

- **Subsystem centrality.** A per-domain scalar derived from domain size, inbound-interaction count, and (optionally) explicit consultant marking. Computed deterministically.
- **Resolution uncertainty.** A scalar derived from which reconciliation rule fired and what its evidence looked like. `manual_override` → 0. `source_authority` with tied weights → high. `llm_judgment` → high.

Within-domain ordering keeps the simple formula.

**What would resolve it.** A change folder that adds these two factors and updates the report rendering. Cheap to implement; can land any time after the consolidate spec is in code.

**Deferred for.** Phase 1 ships with the simple formula; the consultant accepts the noise.

### Q-7 · Conflict feedback loop with the client

**Why it matters.** Top-N conflicts become client questions, the client answers, and the system needs to fold that feedback in and surface the next top-N. The pipeline today produces a static review queue.

**Direction.** Treat client answers as evidence (a new source type or a dedicated `answers/` directory with its own adapter) with high authority. Each conflict gains a lifecycle state (`open | answered | superseded | closed`). A `conflict:resolve <id>` operation accepts feedback, writes it as evidence, re-runs the affected portions of consolidation, and regenerates the review queue.

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

**Why it matters.** The consultant will receive a client-authored estimation report describing planned productization work, with the client's own work estimates. This needs to be ingested, travel through domain-assignment/extraction/consolidation, and be **compared** to our findings (the whole point is to validate the client's estimates). Without source-declared intent, this would produce false status-disagreement conflicts against implemented code.

**Prerequisites resolved.** Projections ([D-49](decisions/0049-projection-primitive.md)) and intent declaration ([D-50](decisions/0050-source-declared-intent.md)) are now in place. Remaining work is a **validation view**: a report section (or separate report) that pairs each client-estimated work item with our findings for the same domain/concept and flags discrepancies.

**What would resolve it.** A change folder that adds the validation view.

**Deferred for.** Needs the validation view design.

### Q-10 · Monolith handling via projections

**Why it matters.** Current scope (35 microservices, 500 KLOC) makes "one repo = one domain seed" reasonable. For future engagements with monoliths, modules within the monolith would need to be identified first and projected separately.

**Direction.** Reuse the projection primitive ([D-49](decisions/0049-projection-primitive.md)). A monolith adapter emits one projection per identified module. No new mechanism needed.

**What would resolve it.** Encountering a monolith.

**Deferred for.** Not relevant to the current engagement.

### Q-11 · Transformation-estimate framing

**Why it matters.** The pipeline is meticulous about producing a high-quality review queue but doesn't show the line from queue to the actual consultant deliverable (transformation scale estimate + Gen-AI acceleration assessment). The reviewer flagged this; the consultant agreed it deserves its own short design.

**Direction (sketch).**

- **Coverage per domain.** For each domain, count requirements by `change_plan_flag` (work to do) vs. implemented. Multiply by domain centrality (from [Q-6](#q-6--top-n-priority-should-include-subsystem-centrality-and-resolution-uncertainty)). Rough effort signal.
- **Validation against client estimate** (from Q-9b). Where do we agree on scope? Where does our scope exceed theirs? Per domain.
- **Gen-AI acceleration heuristic.** Per domain, score along axes the consultant cares about (boilerplate-heavy, well-documented, type-safe domain model, integration-heavy, regulated, etc.). Heuristics, not LLM judgments.

**What would resolve it.** A focused design discussion once the pipeline is producing review queues. Probably a thin downstream layer rather than a pipeline stage.

**Deferred for.** Out of scope for the pipeline spec; in scope for a thin downstream layer to be designed after first runs.

---

## Specific decision flagged for re-examination

### Q-12 · Cross-domain scope ([D-41](decisions/0041-cross-cluster-conservative-scope.md)) — re-examine after first real run

**Why it matters.** The conservative scope excludes three of the five conflict kinds from cross-domain detection. "What part of the change plan crosses subsystem boundaries?" is a question the assessment is trying to answer, and the exclusions might hide signal there.

**What would resolve it.** First real run on the corpus produces actual cross-domain findings. If the consultant finds the conservative scope is leaving important conflicts uncaught, a change folder revisits [D-41](decisions/0041-cross-cluster-conservative-scope.md).

**Deferred for.** Empirical: need data from the first run.

---

## Items dropped from v1 spec with no current trigger

- **Cluster archival** ([D-51] through [D-52] in v0). Not needed in the PoC timeframe. Re-introduce if the pipeline runs long enough to accumulate stale domains.
- **Hierarchical super-domains** ([domain-hierarchy](specs/domain-hierarchy/spec.md)) is **kept** in v1 per consultant request, but flagged as experimental — see the spec for `[NEEDS CLARIFICATION]` markers around proposal/apply workflow.
