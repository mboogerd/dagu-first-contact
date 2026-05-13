# Open Issues — Post-First-Draft Review

Captured after a re-read of `SPECIFICATION.md` and a reviewer pass. Issues are grouped by theme; within each theme they're ordered roughly by how much they should shape the next iteration of the spec. Each issue has a **state** (`open` / `decided` / `deferred`), a short framing, and where useful a sketched direction. Nothing here is a commitment; this is the working set of things to resolve before regenerating the spec.

The over-arching context that re-frames every issue below: this is a **proof-of-concept first**, against a known target (~35 microservice repos, ~500 KLOC, thousands of Jira tickets), to be handed over to another consultant before completion. Simplicity and nimbleness beat completeness. Discipline that pays off in a long-running pipeline (calibration, eval CI) is premature here.

---

## Theme A — Generality of primitives

The current spec is highly coupled to evidence types (jira/git/rfp/spreadsheet/transcript). Several places this looks more specific than the underlying mechanics require.

### [A-1] Evidence-type enum vs directory-as-key  ·  *open*

The `source_type` enum appears in adapters, frontmatter, eval config, source-authority weights, and prompts. In most of those places, the enum is doing the work of "name of the directory the artifact came from." A directory name plus a small adapter registry would carry the same information without spreading an enum across the spec.

**Direction.** Treat `source_type` as a *lookup key* (the adapter's name = the directory under `evidence/`) rather than a typed enum. Adapter registry is `{name → adapter module}`. Per-source config (authority weight, default `evidence_strength`, default `normalization_kind`) is co-located with the adapter, not enumerated centrally. Adding a source type becomes "drop in an adapter," consistent with [D-3] but without the residual coupling.

### [A-2] Operations coupled to evidence types vs projection primitives  ·  *open*

Git is special-cased ([D-22] curated summary). Cross-functional documents (RFPs, spreadsheets) are normalized as single docs, which is wrong for clustering: an RFP that touches five subsystems wants to contribute five partial documents, not one diluted one. Very large evidence (repos) wants multiple projections (architecture summary, public-API surface, domain glossary) rather than one.

**Direction.** Two general primitives instead of one:

- **Projections.** A projection is a (named, deterministic-or-LLM) function from an evidence artifact to a derived doc, preserving provenance back to the source. Git's curated summary is a projection. Splitting an RFP into per-section partials is a projection. Both go into `normalized/` as ordinary `NormalizedDoc` records with `projection: <name>` and `parent_evidence: <id>` in frontmatter. The "verbatim as much as possible" preference is a property of projection authors, not a global rule.
- **Multiple projections per evidence.** A single evidence artifact MAY produce 0..N normalized docs via different projections, each going through clustering/extraction independently. This generalizes [D-22] (one repo → one summary doc) and [D-23] (raw evidence remains accessible) into one consistent mechanism.

This also subsumes the "split cross-cutting docs across clusters" intuition: if a projection emits N partials and each lands in a different cluster, that's exactly the desired behavior.

### [A-3] Status (implemented / planned / proposed) is currently a per-extraction guess; should be a property of the source/projection  ·  *open*

The extractor currently infers `status` per requirement based on source-type cues. But "this evidence describes intended state, not built state" is really a property of *the evidence*, not of each requirement in it. The pre-existing client-authored estimation report (see [E-1]) makes this acute: it's planned work, and we don't want false `status_disagreement` conflicts every time the code doesn't yet match.

**Direction.** A projection (or evidence record) declares an `intent: implemented | planned | proposed | mixed` and a `default_status`. Requirements inherit unless the extractor has strong contrary evidence. Cross-status comparisons that would normally produce a `status_disagreement` are suppressed when the difference is explained by the sources' declared intents (e.g., RFP says "planned," code says "implemented" → expected, not a conflict).

This also gives us a clean place to ingest the client's estimation report as just "another source whose intent is `planned`," without bespoke pipeline logic.

---

## Theme B — Clustering and taxonomy

The current spec treats taxonomy discovery (Stage 1.5) and clustering (Stage 3) as nearly independent stages. The reviewer flagged that this is a missed opportunity, and that pure embedding-based clustering is not trustworthy enough on its own.

### [B-1] Use taxonomy/structured signal to reduce LLM clustering candidates  ·  *open*

For sources with strong structured signal (Jira components/epics, repo names, RFP section headers), embeddings are the weakest of the available signals. The current design uses embeddings as the primary clustering signal and lets structured signals influence only via `assignment_hint`.

**Direction.** Reframe Stage 3 as **candidate reduction → LLM assignment**, not "embeddings assign, LLM labels":

1. **Structured pre-grouping** where available (Jira component → repo via a mapping table; RFP section → header keywords). This is the most reliable signal when present.
2. **Embedding similarity** as a fallback ranker for the unmapped tail.
3. **LLM final assignment** for the top-K candidates per doc. The LLM gets the doc, the K candidate clusters' summaries, and decides. Caps cost via K (small) and via cache on `hash(doc + candidate_summaries)`.

This is a bigger structural change than the spec currently anticipates. It probably wants its own design pass; see [F-2] for how to scope it.

### [B-2] Taxonomy discovery should inform clustering, not just extraction  ·  *open*

Discovery already samples docs and learns about structure. Its findings (e.g., "this Jira project consistently tags by component X") could feed the clustering candidate reduction in [B-1] directly. Currently the discovery output is consumed only by extractors.

**Direction.** Discovery emits, in addition to taxonomy values, **clustering hints** per source type (component/repo mappings, header-to-cluster heuristics, naming conventions). These are persisted alongside the locked taxonomy and consumed by Stage 3.

### [B-3] Repo size assumption: microservices vs. monoliths  ·  *open, low priority for current project*

Current scope (~35 services, ~500 KLOC) makes "one repo = one cluster seed" reasonable. For a future client with monoliths, "repo → cluster" is too coarse; modules within the monolith would need to be identified first and projected separately.

**Direction.** Defer. Note in the spec that the seed-from-repo assumption holds while repos are bounded in size. When that breaks, the answer is a projection ([A-2]) that emits per-module summaries, which then seed clusters as usual. No new mechanism needed; reuse the projection primitive.

---

## Theme C — Conflict handling: surfacing and feedback loop

Two gaps the reviewer raised and that aren't well-covered.

### [C-1] Top-N conflicts should reflect sub-system criticality, not just per-item priority  ·  *open*

The current `review_priority` formula is `criticality_numeric * (1 - confidence)`. That's per-item. It does not account for **how central the cluster (subsystem) is to the whole system** — a critical conflict in a peripheral subsystem should not necessarily outrank a less critical conflict in a load-bearing one when reporting at the top level.

It also doesn't well-account for **uncertainty of auto-resolution**: a conflict that was auto-resolved by `source_authority` with weak evidence should rank higher than one resolved confidently by `manual_override`.

**Direction.** Extend the review-priority formula at top-level rendering with two factors:

- **Subsystem centrality.** A per-cluster scalar derived from cluster size, inbound-interaction count, and (optionally) explicit consultant marking. Cluster-level criticality, separate from per-item criticality. Computed deterministically.
- **Resolution uncertainty.** A scalar derived from which reconciliation rule fired and what its evidence looked like. `manual_override` → 0. `source_authority` with tied weights → high. `llm_judgment` → high. Already implicitly available in `Conflict.resolution`; just needs to be surfaced as a numeric.

Formula at top-level (sketch): `item_priority = criticality * (1 - confidence) * (1 + α * resolution_uncertainty) * (1 + β * subsystem_centrality)`. Weights tunable; sensible defaults.

Within-cluster ordering stays the simple formula (centrality doesn't differentiate items in the same cluster).

### [C-2] Conflict resolution as an interactive loop with the client  ·  *open*

The current spec produces a static review queue. In practice, top-N conflicts become **client questions**, the client answers, and the system needs to fold that feedback in and surface the *next* top-N.

This is a workflow concern as much as a data concern. The data part: an answer to a conflict is just another piece of evidence, with the client as a high-authority source. The workflow part: the cycle of "ask, receive, integrate, re-rank" should be a first-class operation.

**Direction.**

- **Client answers as a source.** Add a `client_feedback` source type (or, per [A-1], an `answers/` directory with its own adapter) with high authority weight. An answer to a conflict creates a new evidence artifact tagged with the conflict id it resolves.
- **Resolution operation.** A subcommand `conflict:resolve <id>` or similar takes feedback, writes it as evidence, re-runs the affected portions of consolidation, and regenerates `review_queue.json`. The layered consolidation caching ([D-38]) means the re-run only touches affected groups.
- **Conflict lifecycle.** Each conflict gains a state: `open | answered | superseded | closed`. The review queue filters to `open` by default. `closed` conflicts remain in the artifact for audit.

This is the highest-value workflow improvement in the doc. The rest of the pipeline already supports it structurally; what's missing is naming the operation and tracking conflict state.

---

## Theme D — Scope reductions for the proof-of-concept

The spec is over-engineered for a one-shot PoC. Several things should be cut or simplified for phase 1 and re-introduced later if the pipeline survives the assessment.

### [D-1] Drop calibration entirely for phase 1  ·  *decided*

[D-39] (the spec's calibration loop) won't get used. The consultant has confirmed they will not author calibration cases. Keep the deterministic confidence formula with default weights; remove `config/calibration/`, `calibrate:run`, `calibrate:accept`, and `CalibrationCase` / `CalibrationRun` schemas from the v1 spec. Note as a deferred enhancement.

Consequence: confidence weights are guesses. Acceptable for PoC; surfaced as a known limitation in the report's freshness section ([D-47] adapts trivially).

### [D-2] Drop the eval framework for phase 1  ·  *decided*

The full eval framework (per-extractor styles, judge prompts, eval cache, `EvalCase` / `EvalRun` / `JudgeVerdict`, five eval sets, `config/eval.yaml`, `config/evals/*/`) is excessive for a PoC. The consultant accepts LLM-generated prompts with manual spot-checks and adjustments.

Keep:
- Prompt versioning (a hash in the prompt file's frontmatter; part of cache keys). Cheap and useful.
- Manual spot-check capability (running an extractor against a single normalized doc and inspecting output). This already falls out of the cache mechanics.

Drop everything else from v1. Note as a deferred enhancement for "once the pipeline shape is stable."

This is a significant complexity reduction. Stage 1.5's discovery loop survives — it isn't eval, it's bootstrapping the taxonomy.

### [D-3] Defer cross-cluster reconciliation polish  ·  *open, leaning defer*

Stage 4.5 is well-designed but it's a phase that adds real cost and complexity. For phase 1, run it but with a high embedding threshold (catch only obvious cases) and `needs_review` cases get surfaced without the boost machinery. Skip the `cross_cluster_boost` calibration question entirely. Re-enable the fuller design only if the first run shows cross-cluster conflicts are a real driver of the review queue.

### [D-4] Defer archival semantics  ·  *deferred*

[D-49]–[D-52] (archival) are well-thought-out and irrelevant in phase 1. Strip from the v1 spec; re-add when the pipeline runs long enough to accumulate stale clusters.

### [D-5] Defer hierarchical super-clustering  ·  *deferred*

Stage 3c (`identifySuperClusters`) is also irrelevant for ~35 microservices. Flat clustering with seed clusters per repo is sufficient. Re-add when a future client's scale makes hierarchy useful.

---

## Theme E — New requirements not in the current spec

### [E-1] Ingest the client's pre-existing estimation report  ·  *open*

The consultant will receive a client-authored estimation report (or sources) describing planned productization work, with the client's own work estimates. This needs to:

- Be ingested via the same projection mechanism ([A-2]), likely as one or more projections of a larger document.
- Travel through clustering, extraction, and consolidation **without producing false `status_disagreement` conflicts** against implemented code. Handled by [A-3] (source-declared intent).
- Be **comparable** to our derived findings — the whole point is to validate the client's estimates. The review queue should surface where our analysis disagrees with theirs (different scope, missed work, optimistic effort), not where their "planned" disagrees with our "implemented."

**Direction.** Once [A-2] and [A-3] are in place, this is mostly automatic. The remaining work is a **validation view**: a report section (or separate report) that pairs each client-estimated work item with our findings for the same cluster/concept and flags discrepancies. Probably best as a dedicated downstream consumer of `review_queue.json` filtered to client-estimate items, not a new pipeline stage.

Some teams may have captured planned work as Jira stories already, which means the planned/implemented mixing happens within Jira too. [A-3] handles this if Jira tickets can carry per-ticket intent (typically: status `to-do` → planned, `done` → implemented). Existing Jira `status` already encodes this; the extractor just needs to map it correctly.

### [E-2] Handover documentation  ·  *open*

The PoC will be handed to another consultant before completion. The current spec has provenance and freshness signals but no explicit "state of play" handover artifact. The report ([D-45]) is closest but is a snapshot of findings, not a runbook.

**Direction.** A single `HANDOVER.md` (or templated section in the report) that captures: what's been run, what's been answered by the client, which conflicts are open and why, where the consultant's attention should go first, and the practical commands for the next consultant to resume. Generated from existing artifacts; deterministic; no LLM. Belongs in v1 because the handover is in scope of the engagement.

### [E-3] Transformation-estimate framing  ·  *open*

The reviewer flagged that the spec is meticulous about producing a high-quality review queue but doesn't show the line from queue to the actual deliverable (transformation scale estimate + Gen-AI acceleration assessment). The consultant has acknowledged this and is open to suggestions.

**Direction.** Out of scope for the pipeline spec; in scope for a thin downstream layer. A first sketch:

- **Coverage per cluster.** For each cluster, count requirements by `change_plan_flag` (work to do) vs. implemented. Multiply by cluster centrality ([C-1]). This is the rough effort signal.
- **Validation against client estimate** ([E-1]). Where do we agree on scope? Where does our scope exceed theirs? Where does theirs exceed ours? Per cluster.
- **Gen-AI acceleration heuristic.** Per cluster, score along axes the consultant cares about (boilerplate-heavy, well-documented, type-safe domain model, integration-heavy, regulated, etc.). Heuristics, not LLM judgments; the consultant adjusts. The output is a per-cluster modifier on estimate.

This deserves its own short design doc once the pipeline is producing review queues. Not blocking for v1.

---

## Theme F — Spec organization for ticket generation

The reviewer asked whether the current spec organization (what/how/why interleaved) is optimal for generating implementation work packages. Short answer: **no**, and there are concrete patterns worth borrowing.

### [F-1] Restructure: split stable specs from per-change deltas  ·  *open*

Researched three established patterns: BMAD-METHOD, OpenSpec, and GitHub's spec-kit. OpenSpec's model is the strongest fit. Adapting it for this project:

**Stable layer** — the long-lived contract:
- `principles.md` — current §1 (the immutable constraints).
- `specs/<component>/spec.md` — per-component behavior contracts, externally-observable only. Likely components: `ingest`, `projection`, `taxonomy`, `extract`, `cluster`, `consolidate`, `report`. Anything that can change without changing observable behavior does NOT go here.
- `decisions/<NNNN>-<slug>.md` — current §4 design decisions, one per file, ADR-style (Context / Decision / Consequences / Alternatives). Existing `[D-N]` references stay valid as filename slugs.
- `risks.md` — current §5 risks/open questions.

**Change layer** — the unit the LLM agent implements:
```
changes/<NNN>-<slug>/
  proposal.md   # what & why, scope (in/out)
  design.md     # decisions specific to this change
  tasks.md      # numbered, parallelizable checklist
  specs/        # delta against the stable layer
```

Each change folder is the "ticket." On merge, the delta integrates into the stable layer.

This is a real restructuring effort, not a re-format. It should happen *before* the next round of significant spec changes, so the rewrites land in the right shape.

### [F-2] Adopt three concrete spec-kit techniques  ·  *open*

Layered on top of [F-1]:

- **`[NEEDS CLARIFICATION: ...]` markers** in proposals. When generating a change from a section of the existing spec, the LLM must mark ambiguities explicitly instead of guessing. Eliminates a class of silent assumptions.
- **A short constitution file** (= `principles.md` for our purposes) that's injected into every generation prompt. Keeps the eight principles from §1 alive across every change.
- **Parallel markers (`[P]`) on tasks** to make agent execution plans explicit. Cheap; useful when tasks fan out.

### [F-3] First batch of change folders to cut from the existing spec  ·  *open*

Once [F-1] is in place, an initial sequence of changes that produces a runnable PoC. Sketch:

1. `001-evidence-and-projections` — adapter registry, projection primitive, the first two adapters (git, jira). Drops the `source_type` enum.
2. `002-normalization-pipeline` — `normalized/`, frontmatter schema, content-hash caching skeleton.
3. `003-taxonomy-discovery` — Stage 1.5, simplified (no eval).
4. `004-extraction` — three extractors, prompt versioning only (no eval framework).
5. `005-clustering-v0` — embedding-based assignment + repo seeds, the simple version. No HDBSCAN, no hierarchy, no archival.
6. `006-consolidation-v0` — bottom-up, deterministic confidence with default weights, LLM criticality. No cross-cluster yet.
7. `007-report-v0` — review queue + landscape + provenance sections.
8. `008-client-feedback-loop` — [C-2], the conflict-resolution operation and conflict state tracking.
9. `009-cross-cluster` — Stage 4.5 in its conservative form ([D-3] above).
10. `010-client-estimate-validation` — [E-1] + [E-3] sketch.

Each is small enough to be implemented in a focused session. The first runnable version is after change `007`. Calibration and full eval framework do not appear; they reappear as later change folders if and when the pipeline outlives the PoC.

---

## Theme G — Reviewer items revisited

Brief notes on the reviewer's seven items in light of the consultant's responses.

- **G-1 (calibration won't happen).** Captured as [D-1]. Eliminates a complexity surface.
- **G-2 (eval is excessive for phase 1).** Captured as [D-2]. Eliminates a major complexity surface.
- **G-3 (microservices vs. monolith assumption).** Captured as [B-3]. Defer; the projection primitive ([A-2]) handles it when needed.
- **G-4 (scale: 35 repos, 500 KLOC, thousands of tickets).** Comfortably within "medium scale." No design changes needed; reaffirms the filesystem-as-DB and sidecar-embedding choices.
- **G-5 (path to transformation estimate).** Captured as [E-3]. Out of pipeline scope; deserves its own short design doc later.
- **G-6 (cross-cluster scope is conservative — to discuss separately).** Not pursued further here; flagged for a separate conversation. Phase 1 keeps it conservative per [D-3].
- **G-7 (handover).** Captured as [E-2]. Belongs in v1.

---

## Recommended order of attack

If I were sequencing the next few hours of spec work:

1. **Restructure first** ([F-1]) — once the doc is split into stable + decisions + changes, every subsequent edit lands in the right place. Doing this after more changes pile on is more expensive.
2. **Cut what doesn't survive phase 1** ([D-1], [D-2], [D-4], [D-5]) — these are deletions; do them while restructuring so the new structure is clean.
3. **Introduce the projection primitive** ([A-2]) and rework [A-1], [A-3] on top of it. This is the biggest conceptual change and unlocks [E-1] cleanly.
4. **Rework clustering** ([B-1], [B-2]) — the second-biggest change. Requires the projection work to be solid first.
5. **Add the feedback loop** ([C-2]) and the centrality/uncertainty extensions to priority ([C-1]) — workflow-shaped changes once the underlying primitives are in place.
6. **Add the two consultant-facing artifacts**: handover ([E-2]) and the estimate-validation sketch ([E-3]).

Cross-cluster polish ([D-3]) and the deferred items remain deferred.
