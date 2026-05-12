# Assessment Pipeline Specification

A reproducible, LLM-augmented pipeline for ingesting heterogeneous evidence about an existing software system, organizing it into emergent clusters, and producing a prioritized human-review queue of requirements and conflicts.

**Purpose of this assessment:** establish a baseline understanding of a client's AWS SaaS solution — its software landscape, requirements, and unimplemented change plan — sufficient to estimate the scale of an on-premise transformation and judge how much of that work can be accelerated with Gen-AI.

**Scope of this document:** the pipeline that produces the artifacts the consultant will read. The consultant's report is out of scope.

---

## 1. Principles

These are the immutable constraints. Every design decision must respect them; deviations require explicit justification in §4.

1. **Filesystem is the database.** Every artifact is a file. Git tracks everything. No external state stores.
2. **Immutable layers.** Each pipeline stage reads from upstream and writes to its own directory. Never mutate upstream.
3. **Content-addressed caching.** Every LLM call is keyed on `hash(prompt + input + model + schema)`. Re-runs are nearly free.
4. **Uniform document shape after ingestion.** All evidence becomes `{markdown + YAML frontmatter}`. Everything downstream is source-agnostic.
5. **Deterministic orchestration, LLM-powered steps.** Plain code orchestrates the pipeline graph. LLMs do work *inside* steps, not *between* them.
6. **Structured outputs only.** No freeform JSON-in-markdown. Use provider structured-output / tool-calling. Every extractor has a schema.
7. **Provenance is preserved end-to-end.** Every derived artifact records its inputs (content hashes), the model, and the prompt version that produced it.
8. **Cheap-first.** Embeddings before LLMs. Cheap models for high-volume mechanical work. Expensive reasoning models reserved for consolidation.

---

## 2. Architecture

### 2.1 Layers

The pipeline has five layers. Each is a directory; each is produced by one stage; none is mutated by downstream stages.

| # | Layer        | Directory       | Produced by stage | Contents                                                  |
|---|--------------|-----------------|-------------------|-----------------------------------------------------------|
| 1 | Evidence     | `evidence/`     | Ingest            | Raw artifacts pulled from source, organized by source type |
| 2 | Normalized   | `normalized/`   | Ingest            | Uniform `{markdown + frontmatter}` view of every artifact  |
| 3 | Extracted    | `extracted/`    | Extract           | Structured JSON extractions per document                   |
| 4 | Clusters     | `clusters/`     | Cluster           | Emergent organization; summaries; membership               |
| 5 | Consolidated | inside clusters | Consolidate       | Conflict-resolved requirements and review queue            |

Plus two cross-cutting:
- `cache/` — LLM call cache, keyed by content hash. Committed to git.
- `config/` — sources, model pins, versioned prompts.

### 2.2 Directory layout

```
assessment/
├── config/
│   ├── sources.yaml              # what to ingest
│   ├── models.yaml               # which model for which step, pinned versions
│   └── prompts/                  # versioned prompt templates
│       ├── extract_requirements.md
│       ├── extract_interactions.md
│       ├── label_cluster.md
│       └── consolidate.md
│
├── evidence/                     # LAYER 1: immutable raw ingested data
│   ├── git/<repo>/...
│   ├── jira/<project>/<ticket>.md
│   ├── spreadsheets/<name>.csv
│   ├── rfp/<doc>.md
│   └── transcripts/<name>-<date>.md
│
├── normalized/                   # LAYER 2: uniform shape
│   └── <source_type>/<source_id>.md
│
├── extracted/                    # LAYER 3: structured extractions
│   └── <source_type>/<source_id>/
│       ├── requirements.json
│       ├── interactions.json
│       └── domains.json
│
├── clusters/                     # LAYER 4: emergent organization
│   ├── _index.yaml               # tree structure + cluster metadata
│   └── <cluster-name>/
│       ├── summary.md            # responsibilities, interactions
│       ├── members.yaml          # normalized doc IDs in this cluster
│       ├── consolidated/         # LAYER 5: lives inside clusters
│       │   ├── requirements.json
│       │   └── review_queue.json
│       └── <sub-cluster>/...
│
├── cache/                        # LLM call cache (committed)
│   └── <hash>.json
│
└── review_queue.json             # top-level merged + re-sorted queue
```

### 2.3 Data shapes

These are the contracts between stages. Changing them is a breaking change to the pipeline.

#### NormalizedDoc (file in `normalized/`)

Markdown file with YAML frontmatter:

```yaml
---
source_type: jira | git | rfp | spreadsheet | transcript
source_id: <stable id, e.g. PROJ-123, repo-name, doc-filename>
source_date: <ISO date if known>
ingested_at: <ISO timestamp>
content_hash: <sha256 of normalized markdown body>
original_path: evidence/jira/proj/PROJ-123.md
extra:
  # source-specific metadata
  jira_status: done
  jira_reporter: alice@example.com
---

<markdown body>
```

#### Requirement (entry in `extracted/.../requirements.json`)

```json
{
  "id": "<source_id>:<local-index>",
  "statement": "The system must ...",
  "type": "functional | quality_attribute | constraint | assumption | change_plan",
  "status": "implemented | planned | proposed | abandoned | unknown",
  "source_id": "<NormalizedDoc.source_id>",
  "source_excerpt": "<verbatim quote that justifies this requirement>",
  "source_date": "<from NormalizedDoc>",
  "extracted_by": {
    "model": "<id>",
    "prompt_version": "<hash>"
  }
}
```

**`type` semantics:**
- `functional` — a behavior the system must perform.
- `quality_attribute` — a measurable property the system must exhibit (performance, security, availability, etc.). Replaces the grab-bag "non-functional."
- `constraint` — an external or design constraint the system must respect (regulatory, technology, integration).
- `assumption` — a stated belief about the world that the requirement set depends on. Flagged separately because assumptions are the most likely source of silent conflicts.
- `change_plan` — a requirement describing **unimplemented** future work. First-class because identifying the change plan is a primary goal of the assessment.

**`status` semantics:**
- `implemented` — evidence shows it is in production (typically from code or "done" Jira tickets).
- `planned` — committed to, not yet implemented (Jira backlog, roadmap docs).
- `proposed` — discussed but not committed (RFP, transcripts, draft docs).
- `abandoned` — was planned, then dropped (closed-won't-do tickets, deprecation notes).
- `unknown` — extractor could not determine from the source.

Status is set by the extractor per source. The same requirement appearing in code AND a Jira backlog ticket will produce two `Requirement` rows with different statuses; consolidation reconciles them.

#### Interaction (entry in `extracted/.../interactions.json`)

An **interaction** is a runtime-topology relationship between two software components: one component depending on another for behavior or data at runtime. Out of scope: human collaboration, team ownership, build-time-only dependencies (use cluster metadata for those).

```json
{
  "id": "<source_id>:<local-index>",
  "kind": "http_call | event_publish | event_subscribe | shared_database | shared_cache | message_queue | rpc | webhook | file_transfer",
  "participants": {
    "from": "<component identifier, e.g. service or repo name>",
    "to": "<component identifier>",
    "bidirectional": false
  },
  "endpoint": {
    "present": true,
    "value": "POST /payments/{id}/refund",
    "protocol": "https"
  },
  "evidence_strength": "observed | documented | inferred",
  "evidence_excerpt": "<verbatim quote from source>",
  "source_id": "<NormalizedDoc.source_id>",
  "source_date": "<from NormalizedDoc>",
  "extracted_by": {
    "model": "<id>",
    "prompt_version": "<hash>"
  }
}
```

**Component identifier convention.** Use stable, repo-derived names where possible (e.g., `payments-service`, not "the payments thing"). External systems use a `external:` prefix (e.g., `external:stripe-api`). Unknown participants use `unknown:<descriptor>`.

**`kind` semantics:**
- `http_call` — synchronous HTTP/REST request, including GraphQL over HTTP.
- `event_publish` / `event_subscribe` — pub/sub events (Kafka, EventBridge, SNS topics). Two separate kinds because a component's role matters for impact analysis.
- `shared_database` — two components reading/writing the same database.
- `shared_cache` — two components reading/writing the same cache (Redis, Memcached).
- `message_queue` — point-to-point queue (SQS, RabbitMQ direct exchange).
- `rpc` — gRPC, Thrift, language-native RPC.
- `webhook` — async HTTP callback. Distinct from `http_call` because the direction is reversed relative to setup.
- `file_transfer` — S3 hand-off, SFTP, shared filesystem, batch file drop.

**`participants` rules:**
- `from` and `to` SHOULD be set when the extractor can determine direction.
- `bidirectional: true` when the relationship is genuinely two-way (e.g., shared database with both sides read/write).
- When direction cannot be determined from evidence, set `from` and `to` to the same alphabetically-sorted pair and `bidirectional: true` — never invent direction.

**`endpoint` rules:**
- `present: true` with a meaningful `value` whenever evidence reveals it (URL path, event name, queue name, table name).
- `present: false` for service-level-only interactions (e.g., "checkout-service uses payments-service" without specifics).
- For event/queue interactions, `value` is the topic/queue name. For shared data, `value` is the table/object identifier.

**`evidence_strength` semantics:**
- `observed` — extracted from code, config, OpenAPI specs, or other artifacts that *implement* the interaction. Treat as fact.
- `documented` — extracted from docs, RFPs, tickets, or transcripts that *describe* the interaction. Treat as claim.
- `inferred` — not explicitly stated but strongly implied by context (e.g., a service named `payments-api` referenced by name in a checkout flow doc, with no concrete API call shown). Treat as hypothesis.

Downstream consumers (cluster summaries, landscape diagrams, impact analysis) MAY filter or weight by `evidence_strength`.

**Per-source extraction guidance:**

| Source       | Typical `kind` values                                   | Typical `evidence_strength` |
|--------------|---------------------------------------------------------|----------------------------|
| `git`        | All kinds, depending on code / config / OpenAPI present | `observed`                 |
| `jira`       | Whatever the ticket describes                            | `documented`               |
| `rfp`        | Mostly `http_call`, `event_*`, `file_transfer`           | `documented`               |
| `spreadsheet`| Often `http_call` or `file_transfer` (integration lists) | `documented`               |
| `transcript` | Whatever is said                                         | `documented` or `inferred` |

#### Domain (entry in `extracted/.../domains.json`)

A **domain** is a named concept the system organizes itself around. Two kinds are tracked explicitly because they answer different questions.

```json
{
  "id": "<source_id>:<local-index>",
  "kind": "business_domain | technical_domain",
  "name": "Payments",
  "aliases": ["payment processing", "billing"],
  "description": "Concise statement of what this domain covers, in the source's own framing.",
  "evidence_excerpt": "<verbatim quote from source>",
  "source_id": "<NormalizedDoc.source_id>",
  "source_date": "<from NormalizedDoc>",
  "extracted_by": {
    "model": "<id>",
    "prompt_version": "<hash>"
  }
}
```

**`kind` semantics:**
- `business_domain` — a business capability or problem area (DDD-style). Examples: `Payments`, `Onboarding`, `Claims`, `Reporting`. Answers "what does the business do here?"
- `technical_domain` — an implementation-side area or concern. Examples: `Authentication`, `Event Bus`, `Data Warehouse`, `Frontend Shell`. Answers "what part of the technical stack is this?"

A single source can yield both kinds. The same concept may legitimately appear under both kinds (e.g., "Payments" as a business domain AND a technical subsystem); these are separate entries.

**`aliases` rationale.** Sources often use varying terminology for the same concept. Aliases are captured at extraction time and used during consolidation to merge entries.

#### Cluster entry (in `clusters/_index.yaml`)

```yaml
- name: payments-service
  path: clusters/payments-service
  parent: clusters/financial-domain   # null if root
  archived: false
  member_count: 47
  summary_hash: <hash of summary inputs>   # cache key
  seeded_from: git:payments-service        # provenance of cluster creation
```

#### ConsolidatedRequirement (in `consolidated/requirements.json`)

```json
{
  "id": "<cluster>:<index>",
  "statement": "<resolved canonical statement>",
  "sources": [
    {"requirement_id": "...", "source_id": "...", "source_date": "..."}
  ],
  "conflict": {
    "present": true,
    "description": "Source A says X; source B says Y",
    "resolution_rationale": "Source A is more recent and from authoritative RFP"
  },
  "confidence": 0.0,        // 0..1
  "criticality": 0.0,       // 0..1
  "review_priority": 0.0,   // criticality * (1 - confidence), tunable
  "resolved_by": {
    "model": "...",
    "prompt_version": "..."
  }
}
```

#### ReviewQueueItem (in `review_queue.json`)

A flat sortable list. Same shape as `ConsolidatedRequirement` plus:

```json
{
  "cluster_path": "clusters/financial-domain/payments-service",
  "...": "<all ConsolidatedRequirement fields>"
}
```

---

## 3. Pipeline

Five stages. Each stage follows the same sub-template:

- **Purpose** — one line.
- **Input → Output** — which layers.
- **Approach** — deterministic? LLM? what's cached?
- **Key decisions** — references into §4.
- **Failure modes** — what can silently go wrong here.

### Stage 1 · Ingest

**Purpose.** Pull raw evidence from sources; produce uniform normalized docs.

**Input → Output.** `config/sources.yaml` → `evidence/` + `normalized/`.

**Approach.** Per-source-type adapters. Each adapter has two responsibilities:
1. Fetch raw evidence into `evidence/<source_type>/...` (idempotent — skip if unchanged).
2. Produce a `NormalizedDoc` (markdown + frontmatter) in `normalized/<source_type>/<source_id>.md`.

Adapters in scope for v1: `git`, `jira`, `spreadsheet`, `rfp`, `transcript`. Adding a new source type means writing one adapter; nothing downstream changes.

**Key decisions.** [D-1 Filesystem-as-DB], [D-2 Uniform doc shape], [D-3 Adapter pattern].

**Failure modes.**
- Lossy normalization (e.g., spreadsheets with rich formatting flattened too aggressively).
- Stale `evidence/` if upstream changed but our cache says "fetched recently."
- Spreadsheets and RFPs that defy markdown conversion (large tables, embedded images).
- Jira tickets with thousands of comments blowing past context windows in later stages.

### Stage 2 · Extract

**Purpose.** Derive structured information of interest (requirements, interactions, domains) from normalized docs.

**Input → Output.** `normalized/` → `extracted/`.

**Approach.** Three source-agnostic extractors run independently per document:

1. **`extract_requirements`** — produces `Requirement` rows (§2.3). Captures `type` (functional / quality_attribute / constraint / assumption / change_plan) and `status` (implemented / planned / proposed / abandoned / unknown). Status MUST be set per source; the extractor uses `source_type` and source-specific cues as context to infer status (e.g., closed Jira ticket → likely `implemented` or `abandoned` depending on resolution; RFP statement → likely `proposed` or `planned`).

2. **`extract_interactions`** — produces `Interaction` rows (§2.3) for **runtime topology only**. Captures `kind`, `participants` (with explicit `bidirectional` flag when direction is unclear), `endpoint` (when available; degrades to service-level when not), and `evidence_strength` (observed / documented / inferred — see §2.3 for source-to-strength mapping). Human collaboration, team ownership, and build-time-only dependencies are **out of scope** and MUST NOT be emitted.

3. **`extract_domains`** — produces `Domain` rows (§2.3) of two kinds: `business_domain` and `technical_domain`. Both kinds may appear from the same source; the same concept may legitimately appear as both kinds with separate entries. Aliases are captured at extraction time to support consolidation merging.

Each extractor:
- Has its own prompt template in `config/prompts/`.
- Reads the full `NormalizedDoc`; `source_type` from the frontmatter is *context*, not *control flow*.
- Produces structured JSON via provider tool-calling, validated against the schema in §2.3.
- Has its own eval set ([D-6], [OPEN-2]).

Every extraction call goes through the LLM cache (Principle 3). Cache key: `hash(prompt_text + doc_content_hash + model_id + schema)`.

**Key decisions.** [D-4 Source-agnostic extractors], [D-5 Structured outputs only], [D-6 Per-extractor eval set], [D-16 Three explicit extractors].

**Failure modes.**
- Silent under-extraction (LLM returns three requirements where there are ten). Mitigation: small per-extractor eval set (§6, [OPEN-2]).
- Inconsistency across re-runs when prompts change. Mitigation: prompt versioning is part of the cache key.
- Hallucinated `source_excerpt` / `evidence_excerpt` values not actually present in the doc. Mitigation: post-extraction validation that excerpts are substrings of the source.
- **Interaction over-extraction.** Extractor invents a direction from ambiguous evidence. Mitigation: schema requires `bidirectional: true` when direction can't be determined; eval set MUST include ambiguous-direction examples.
- **Interaction scope creep.** Extractor emits human-collaboration relationships ("Alice handed off to Bob"). Mitigation: prompt explicitly forbids; eval set includes negative examples.
- **Domain proliferation.** Every minor noun becomes a domain. Mitigation: prompt requires a minimum specificity threshold (a domain is something the source treats as a *named, scoped concept*, not any mentioned topic).
- **Status mis-classification.** Same code-implemented feature also has a stale "planned" Jira ticket; both extract correctly, consolidation must reconcile. Not a failure — by design.

### Stage 3 · Cluster

**Purpose.** Organize normalized docs into an emergent hierarchy reflecting the system's structure.

**Input → Output.** `normalized/` + `extracted/` → `clusters/`.

**Approach.** Four phases. The first is deterministic; the rest are LLM-driven but cached.

**3a. Structural (deterministic).**
- Compute embeddings for every `NormalizedDoc` (cheap embedding model, cached on content hash).
- **Seed clusters from non-archived git repos** — repos reflect actual team/system boundaries and provide a strong prior.
- For non-git docs: assign to nearest repo-cluster by embedding cosine similarity above a threshold. Below threshold, leave unassigned.
- Optionally: run HDBSCAN (fixed seed) on unassigned docs to surface orphan clusters.
- Result: a flat assignment of every doc to a cluster (or "unassigned").

**3b. Semantic labeling (LLM, cached).**
- For each cluster, generate `summary.md` covering responsibilities and interactions, from member docs and their extractions.
- Cache key: `hash(sorted(member_content_hashes) + prompt_version + model)`.
- Summary only regenerates when membership or member content changes.

**3c. Hierarchy (LLM, low frequency).**
- `identifySuperClusters`: given sibling cluster summaries within a path, propose groupings.
- Output is a proposed tree edit applied to `_index.yaml`.
- Re-summarization of new parents cascades but is cached, so unchanged subtrees cost nothing.

**3d. Archival.**
- Manual flag in `_index.yaml`. Archived clusters are skipped in all subsequent summarization and consolidation.

**Key decisions.** [D-7 Embeddings-first clustering], [D-8 Git repos as seed], [D-9 Hash-keyed summary cache].

**Failure modes.**
- Misfiled docs from embedding-only assignment (e.g., a Jira ticket semantically near repo A but actually about repo B). Mitigation: surface low-confidence assignments for review; allow explicit hints in normalized frontmatter (e.g., Jira `component` → repo mapping).
- Super-cluster proposals that over-merge unrelated subsystems. Mitigation: human review at hierarchy phase; conservative thresholds.
- Embedding model drift between runs if model is unpinned. Mitigation: §4 [D-12 Pinned models].

### Stage 4 · Consolidate

**Purpose.** Group extracted requirements per cluster, surface conflicts, resolve them with provenance, and score for human review priority.

**Input → Output.** `clusters/` + `extracted/` → `clusters/**/consolidated/`.

**Approach.** Runs bottom-up through the cluster tree. At each cluster:

1. **Gather.** All extracted requirements from member docs + already-consolidated requirements from child clusters.
2. **Group.** Semantically (embedding similarity → LLM verification).
3. **Detect conflicts.** Within each group, identify contradictions, scope differences, version skew.
4. **Resolve.** Apply provenance rules in this order:
   - Explicit override in `config/` (rare, manual).
   - Source authority weights from `config/` (e.g., RFP > Jira > transcripts).
   - Recency (more recent wins, all else equal).
   - LLM judgment with rationale recorded.
5. **Score.**
   - `confidence`: how sure the resolution is. Function of source agreement, recency spread, and LLM self-report.
   - `criticality`: importance to cluster scope. LLM with cluster summary as context.
   - `review_priority`: `criticality * (1 - confidence)`, tunable.
6. **Emit.** `consolidated/requirements.json` and `consolidated/review_queue.json`.

After all clusters: merge and re-sort into top-level `review_queue.json`.

**Key decisions.** [D-10 Provenance-driven resolution], [D-11 Bottom-up consolidation], [D-13 Expensive model here].

**Failure modes.**
- **Cross-cluster conflicts missed.** Bottom-up consolidation catches conflicts within a subtree but not between distant branches. A Jira ticket in cluster A and an RFP requirement in cluster B may contradict and never be compared. Partial mitigation: the root-cluster consolidation pass surfaces what it can; full mitigation is an open question (§6, [OPEN-3]).
- **Confidence/criticality miscalibration.** Initial scoring will be noisy. Plan to hand-label ~50 items and tune scoring before trusting the queue.
- **Provenance authority weights are guesses.** RFP isn't always more authoritative than Jira if the Jira is from last week and the RFP is from last year. Recency-vs-authority trade-offs should be configurable, not hardcoded.

### Stage 5 · Orchestration

**Purpose.** Sequence stages with incremental, content-addressed execution.

**Approach.** Plain Python entrypoint, explicit subcommands:

```bash
python -m assessment ingest        # idempotent; only fetches changed sources
python -m assessment extract       # only runs on changed normalized docs
python -m assessment cluster       # phases 3a-3d, configurable depth
python -m assessment consolidate   # bottom-up
python -m assessment report        # generates the human-facing summary
```

Each stage:
- Reads its inputs.
- Computes a content hash of inputs.
- Skips work if outputs exist and input hashes match.
- Writes outputs.

This gives `make`-like incremental behavior without `make`.

**Key decisions.** [D-14 Deterministic orchestration], [D-15 Stage-level incremental execution].

**Failure modes.**
- Hidden state in adapters (e.g., API rate-limit retries that aren't deterministic).
- Cache invalidation bugs — output exists but inputs changed in a way the hash didn't catch.
- Partial failures leaving inconsistent state (e.g., half a cluster's docs re-extracted, half not). Mitigation: stage operations are per-document; resume is safe.

---

## 4. Design Decisions

Each entry: *Decision · Rationale · Alternatives considered · Trade-offs accepted.*

### [D-1] Filesystem-as-DB
**Decision.** Use the filesystem as the primary store; commit everything to git.
**Rationale.** For a one-shot consulting assessment at medium scale, filesystem beats any DB on simplicity, greppability, diffability, portability, and reproducibility. Git tracks the full state.
**Alternatives.** SQLite (more queryable but binary), DuckDB+Parquet (good for analytics but adds tooling), a vector DB (overkill at this scale).
**Trade-offs.** Cross-document queries require ad-hoc scripts. Acceptable: queries are infrequent and the consultant is the user.

### [D-2] Uniform normalized-doc shape
**Decision.** All ingested artifacts become `{markdown + YAML frontmatter}` with a fixed frontmatter schema.
**Rationale.** Lets every downstream stage be source-agnostic. Adding a new source type doesn't ripple.
**Alternatives.** Per-source-type schemas through the pipeline.
**Trade-offs.** Some source-specific information lives in the `extra:` frontmatter field; extractors can use it but shouldn't require it.

### [D-3] Adapter pattern for ingestion
**Decision.** One adapter per source type, single-purpose: fetch + normalize.
**Rationale.** New source types = new file. No changes to extractors, clustering, or consolidation.
**Alternatives.** One mega-ingestor with conditional branches.
**Trade-offs.** Some code duplication across adapters (e.g., date parsing).

### [D-4] Source-agnostic extractors
**Decision.** One prompt per extraction type, regardless of source. `source_type` is context, not control flow.
**Rationale.** Prevents prompt drift across source-specific extractors. Keeps eval sets manageable.
**Alternatives.** Per-source extractors (`extractRequirementsFromGit`, etc., as in the original draft).
**Trade-offs.** A single prompt must handle the variance across sources. Mitigated by including `source_type` and a short style-guide-per-source in the prompt template.

### [D-5] Structured outputs only
**Decision.** Every LLM extraction uses provider structured-output / tool-calling against a JSON schema. No JSON-in-markdown.
**Rationale.** Eliminates a whole class of parsing failures. Schema doubles as documentation.
**Alternatives.** Freeform with regex parsing.
**Trade-offs.** Provider lock-in to structured-output APIs. Acceptable for a one-shot assessment.

### [D-6] Per-extractor eval set
**Decision.** Each extractor has a small (10–20 examples) hand-labeled eval set. Re-run on every prompt or model change.
**Rationale.** The only defense against silent extraction regression when iterating on prompts.
**Alternatives.** Spot-checking. Trusts the LLM too much.
**Trade-offs.** Up-front labeling effort. (Estimated 1–2 hours per extractor.)

### [D-7] Embeddings-first clustering
**Decision.** Structural clustering is embedding-based and deterministic. LLMs only label and summarize.
**Rationale.** LLM clustering of thousands of docs is non-deterministic, expensive, and hard to reproduce. Embeddings + fixed-seed clustering give the same tree on every run; LLMs handle the parts they're good at.
**Alternatives.** Pure LLM clustering (rejected: non-determinism), pure embedding clustering with no labels (rejected: opaque).
**Trade-offs.** Embedding-based assignment makes some semantic mistakes (see Stage 3 failure modes).

### [D-8] Git repos as cluster seeds
**Decision.** Initial clusters are seeded from non-archived git repos. Other docs assigned to the nearest repo cluster.
**Rationale.** Repos are a strong prior — they reflect team and system boundaries. Better starting point than asking an LLM to invent a taxonomy.
**Alternatives.** Pure unsupervised clustering on embeddings (rejected: less stable, less explainable).
**Trade-offs.** Bias toward existing repo structure. If the repo structure is wrong (monolith, or wrong split), clusters inherit that. Acceptable: an assessment that mirrors current structure is useful even if structure is suboptimal.

### [D-9] Hash-keyed summary cache
**Decision.** Cluster summary cache key is `hash(sorted(member_content_hashes) + prompt_version + model)`.
**Rationale.** Recursive summarization with hash-keyed cache keeps cost bounded: unchanged subtrees cost nothing on re-runs.
**Alternatives.** Re-summarize on every run (expensive), or time-based cache (incorrect).
**Trade-offs.** Cache key recomputation is itself work; negligible at this scale.

### [D-10] Provenance-driven conflict resolution
**Decision.** Conflicts resolved by an ordered ruleset: manual override → source authority weights → recency → LLM judgment.
**Rationale.** Deterministic where possible. LLM judgment only as a tiebreaker, with rationale always recorded.
**Alternatives.** Pure LLM judgment (less defensible to the client).
**Trade-offs.** Source authority weights need configuration and tuning.

### [D-11] Bottom-up consolidation
**Decision.** Consolidate leaf clusters first; parents reuse children's consolidated outputs.
**Rationale.** Cheaper, cacheable, follows the cluster hierarchy.
**Alternatives.** Global consolidation in one pass (won't scale; loses cluster context).
**Trade-offs.** Cross-cluster conflicts only surface at common ancestor. See [OPEN-3].

### [D-12] Pinned model versions
**Decision.** `config/models.yaml` pins exact model IDs (e.g., `claude-sonnet-4-5-20250929`). No `*-latest` aliases.
**Rationale.** Reproducibility. A model update mid-assessment otherwise invalidates the cache silently and changes outputs.
**Alternatives.** Latest models (faster to benefit from improvements; not reproducible).
**Trade-offs.** Manual model upgrades required.

### [D-13] Expensive model only at consolidation
**Decision.** Cheap model for extraction (high volume, mechanical). Expensive reasoning model for consolidation (low volume, reasoning-heavy).
**Rationale.** Cost optimization without sacrificing quality where it matters.
**Alternatives.** Same model everywhere (simpler; more expensive).
**Trade-offs.** Two model dependencies instead of one.

### [D-14] Deterministic orchestration, LLMs as workers
**Decision.** Pipeline graph (ingest → extract → cluster → consolidate) is fixed code. LLMs are called from within stages, not asked to orchestrate stages.
**Rationale.** Reproducibility, debuggability, cost predictability. Agent orchestration adds non-determinism exactly where it's most harmful.
**Alternatives.** Agent-based orchestration (initially considered; rejected — see §5 [R-1]).
**Trade-offs.** Less "smart" — the pipeline can't decide to skip a stage or re-route based on findings. A user-facing chat agent over the results is a separate concern.

### [D-15] Stage-level incremental execution
**Decision.** Each stage hashes inputs, skips if outputs exist and match. No external build tool.
**Rationale.** `make`-like behavior in Python is cheap; avoids dependency on `make` or a workflow engine.
**Alternatives.** Prefect/Dagster (overhead too high for one-off assessment).
**Trade-offs.** Custom cache invalidation logic; potential for bugs. Mitigated by keeping the logic small and uniform across stages.

### [D-16] Three explicit extractors with distinct schemas
**Decision.** Three extractors — `extract_requirements`, `extract_interactions`, `extract_domains` — each with its own prompt, schema, and eval set. Interactions are scoped to **runtime topology** only; domains are split into `business_domain` and `technical_domain`; requirements carry both `type` and `status`.
**Rationale.** Each extractor answers a distinct question: "what must the system do?" (requirements), "who talks to whom?" (interactions), "what concepts is the system organized around?" (domains). Mixing them in one extractor produces vague output. Keeping them separate makes prompts focused, eval sets small, and downstream consumers explicit about what they need.
**Alternatives.**
- One mega-extractor producing all three. Rejected: prompt becomes a kitchen sink; eval set becomes unmanageable.
- Two extractors (requirements + topology). Rejected: domains are useful for cluster naming and for linking business capabilities to technical clusters; folding them into requirements muddies the requirements schema.
- Per-source-type extractor variants (`extractRequirementsFromGit`, etc.). Rejected by [D-4]: prompt drift across sources is worse than handling source variance within a single prompt.
**Trade-offs.**
- Three eval sets to maintain instead of one.
- Three LLM calls per document instead of one (cost increase). Mitigated by [D-13]: cheap model for extraction; cache reuse on re-runs.
- Some information is awkward to attribute — e.g., a sentence may imply a requirement, an interaction, AND a domain. Each extractor independently emits its view; that's correct, not duplication.

---

## 5. Known Risks

Risks we've accepted, with mitigations.

### [R-1] Agent-based orchestration appeals; deterministic orchestration was chosen
The user initially leaned toward agent-based execution. We pushed back: agent orchestration stacks non-determinism, makes debugging hard, burns tokens reasoning about work rather than doing it, and undermines reproducibility — exactly where we need it. Decision is [D-14]. If a user-facing chat interface over the assessment results is desired later, it's a separate layer that reads the artifacts the deterministic pipeline produces.

### [R-2] Cross-cluster requirement reconciliation is incomplete
Bottom-up consolidation catches conflicts within a subtree but not between distant branches. Root-cluster consolidation does a partial pass over the global requirement set, but quality degrades with breadth of summary. See [OPEN-3].

### [R-3] Embedding-based cluster assignment will misfile some docs
A Jira ticket can semantically match repo A but actually be about repo B. Mitigations:
- Use explicit hints in normalized frontmatter where available (e.g., Jira `component` → repo mapping).
- Surface low-confidence assignments in a review queue, not silently.
- Accept that 5–10% misfiling is fine at the assessment stage.

### [R-4] Prompt drift invalidates cache
Tuning prompts during the assessment invalidates cached outputs for that extractor. Cache key includes prompt version (so this is *correct*, not buggy), but it means budget for regeneration on prompt changes. Mitigation: stabilize prompts on a small sample before running across all evidence.

### [R-5] Confidence and criticality scoring is uncalibrated initially
First runs will produce a noisy review queue. Plan to hand-label ~50 items after the first full run and tune the scoring before presenting to the client.

### [R-6] Source-authority weights are guesses
RFP isn't always more authoritative than Jira if the Jira is from last week and the RFP is from last year. Weights live in `config/` and should be tuned, not trusted by default.

### [R-7] Lossy normalization for complex sources
Spreadsheets with rich formatting, RFPs with embedded tables/images, and transcripts with speaker overlap may lose information at normalization. Mitigation: preserve original in `evidence/`; surface "normalization warnings" alongside the normalized doc.

### [R-8] Filesystem scaling
At medium scale (dozens of repos, thousands of tickets), the filesystem is fine. If scope grows to large (hundreds of repos, 10k+ tickets), expect: slow `git status`, slow recursive listings, and pressure to introduce an index. Mitigation: revisit at that point, not pre-emptively.

---

## 6. Open Questions / Deep-dive Areas

Unresolved. Each entry: *Question · Why it matters · What would resolve it.*

### ~~[OPEN-1] Concrete definitions of "interaction" and "domain"~~ — RESOLVED
**Status.** Resolved in the v0.2 refinement. See:
- Interactions: §2.3 `Interaction` schema + per-source extraction guidance + Stage 2 prompt scope; [D-16].
- Domains: §2.3 `Domain` schema with `business_domain` / `technical_domain` split; [D-16].
- Requirements `type` and `status` taxonomies were tightened in the same pass.

**Still to do** (now covered by [OPEN-2] and the new [OPEN-8]):
- Build the eval sets that exercise these definitions on real evidence.
- Validate the taxonomy on a sample before running across all evidence.

### [OPEN-2] Eval-set construction strategy
**Why it matters.** Without eval sets, prompt tuning becomes guesswork. With them, every prompt change is checkable.
**What would resolve it.** Decide: how many examples per extractor (probably 15–25), how to source them (hand-picked diverse representatives), what metric (exact match? LLM-as-judge? embedding similarity?), and where they live (`config/evals/<extractor>/`).

### [OPEN-3] Cross-cluster conflict reconciliation
**Why it matters.** The most interesting conflicts are often between subsystems (Jira says X for cluster A, RFP says Y for cluster B, code does Z somewhere else). Bottom-up consolidation underweights these.
**What would resolve it.** Choice between:
1. A final global pass over all consolidated requirements (expensive; loses cluster context).
2. Cross-cluster "conflict candidate" detection via embedding similarity across cluster boundaries, with targeted LLM verification.
3. Accept the limitation; document that distant-branch conflicts are out of scope for the automated pipeline and surface only what root-cluster consolidation finds.

Default recommendation: option 2.

### [OPEN-4] Clustering algorithm specifics
**Why it matters.** [D-7] commits to "embeddings + deterministic clustering" but doesn't specify the algorithm, threshold strategy, or how the threshold is tuned.
**What would resolve it.** Decide: embedding model (pinned), similarity metric, assignment threshold (start at cosine 0.55–0.65 and tune on a holdout set), whether HDBSCAN is part of the default path or only for orphans, fixed seed.

### [OPEN-5] Consolidation schema for requirements — PARTIALLY ADDRESSED
**Progress.** The extracted `Requirement` schema now carries `type` (functional / quality_attribute / constraint / assumption / change_plan) and `status` (implemented / planned / proposed / abandoned / unknown) — see §2.3 and [D-16]. This gives consolidation the inputs it needs.
**Still open.** `ConsolidatedRequirement` itself does not yet propagate `type`, `status`, or the `change_plan` tagging. It also does not capture priority hints from the source. A consolidation deep-dive should:
- Decide whether `ConsolidatedRequirement` carries a single resolved `type` and `status`, or surfaces conflicts in those fields too (e.g., when sources disagree on whether something is implemented).
- Add fields for source-stated priority where available.
- Confirm `change_plan` requirements are highlighted in the review queue regardless of confidence — they are first-class output, not derived.
- Hand-walk 10–20 real requirements through the consolidation logic to validate.

### [OPEN-6] Reporting layer
**Why it matters.** §3 mentions a `report` subcommand but the spec doesn't say what it produces. The consultant's written report is out of scope, but a structured "first read" artifact (top-level summary + landscape map + top-50 review queue items) is useful.
**What would resolve it.** Decide: is the report a single markdown document, a small static site, or just structured JSON the consultant reads in their editor?

### [OPEN-7] What to do with archived clusters' content
**Why it matters.** `archiveCluster` excludes a cluster from summarization and consolidation, but the docs and extractions remain. Should they be visible in search? Excluded from review queue? Useful as historical context?
**What would resolve it.** A short decision on archival semantics. Default proposal: archived clusters are excluded from summarization, consolidation, and the review queue, but remain readable for context.

### [OPEN-8] Taxonomy validation on real evidence
**Why it matters.** The taxonomies introduced in [D-16] (requirement `type`/`status`, interaction `kind`/`evidence_strength`, domain `kind`) are designed up-front. They will only survive contact with real data if validated early. Premature taxonomy lock-in is a worse problem than no taxonomy.
**What would resolve it.** Before running extractors across all evidence:
1. Hand-pick 5–10 diverse normalized docs (one per source type, varied content).
2. Run each extractor with the current prompt/schema.
3. Manually check whether each enum value is sufficient, ambiguous, or unused.
4. Iterate the taxonomy *once* based on findings. Lock it after.

Couples with [OPEN-2] (eval-set construction): the same hand-picked docs seed both the taxonomy validation and the eval set.

---

## 7. Glossary

- **Evidence** — Raw, immutable, ingested artifact in its source-native form.
- **Normalized document** — Uniform `{markdown + frontmatter}` representation of an evidence item.
- **Extraction** — Structured JSON derived from a normalized document (requirements, interactions, domains).
- **Cluster** — A grouping of normalized documents with its own summary and consolidated outputs.
- **Super-cluster** — A parent cluster grouping sibling sub-clusters.
- **Consolidation** — The process of grouping extracted requirements within a cluster, resolving conflicts, and scoring for review.
- **Review queue** — A ranked list of consolidated requirements that need human attention, ordered by `review_priority`.
- **Provenance** — The chain of source artifacts, models, and prompt versions that produced a derived artifact.

---

## 8. Document conventions

- `[D-N]` Design decision, defined in §4.
- `[R-N]` Known risk, defined in §5.
- `[OPEN-N]` Open question / deep-dive area, defined in §6.
- Cross-references use these markers inline; the canonical entry lives in its section.
- Changes to data shapes (§2.3) are breaking changes and require a corresponding decision entry in §4.
- Resolved open questions are kept in §6 with a `RESOLVED` (or `PARTIALLY ADDRESSED`) marker and a pointer to where the resolution lives. They are not deleted, so the history of design moves stays readable.
