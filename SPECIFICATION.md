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

The pipeline has five layers plus two intermediate artifacts. Each layer is a directory; each is produced by one stage; none is mutated by downstream stages.

| # | Layer            | Directory         | Produced by stage              | Contents                                                  |
|---|------------------|-------------------|--------------------------------|-----------------------------------------------------------|
| 1 | Evidence         | `evidence/`       | Ingest                         | Raw artifacts pulled from source, organized by source type |
| 2 | Normalized       | `normalized/`     | Ingest                         | Uniform `{markdown + frontmatter}` view of every artifact  |
| — | Taxonomy         | `taxonomy/`       | Taxonomy Discovery             | Discovery iterations + the locked taxonomy that Extract consumes |
| 3 | Extracted        | `extracted/`      | Extract                        | Structured JSON extractions per document                   |
| 4 | Clusters         | `clusters/`       | Cluster                        | Emergent organization; summaries; membership               |
| 5 | Consolidated     | inside clusters   | Consolidate                    | Conflict-resolved requirements and review queue            |
| — | Cross-cluster    | `cross_cluster/`  | Cross-cluster Reconciliation   | Cross-cluster conflict candidates and verified conflicts   |
| — | Reports          | `reports/`        | Report                         | Timestamped, consultant-facing first-read markdown reports |

Plus two cross-cutting:
- `cache/` — LLM call cache, keyed by content hash. Committed to git.
- `config/` — sources, model pins, versioned prompts. The **locked taxonomy** is also produced into `config/taxonomy.locked.yaml` for downstream stages to consume.

### 2.2 Directory layout

```
assessment/
├── config/
│   ├── sources.yaml              # what to ingest
│   ├── models.yaml               # which model for which step, pinned versions
│   ├── taxonomy.starting.yaml    # starting taxonomy (floor; from §2.3 enums)
│   ├── taxonomy.locked.yaml      # locked taxonomy produced by Stage 1.5
│   ├── clustering.yaml           # embedding model, threshold, HDBSCAN params, seed
│   ├── eval.yaml                 # judge model pin, per-extractor thresholds
│   ├── consolidation.yaml        # source authorities, confidence weights, scoring params
│   ├── report.yaml               # top-N size, freshness thresholds, section toggles
│   ├── evals/                    # eval sets, one directory per LLM-driven step
│   │   ├── summarize_repo/
│   │   │   ├── cases/<case_id>.yaml
│   │   │   └── runs/<run_id>.json
│   │   ├── discover_taxonomy/
│   │   ├── extract_requirements/
│   │   ├── extract_interactions/
│   │   └── extract_domains/
│   ├── calibration/              # consolidated-scoring calibration set + runs
│   │   ├── cases/<case_id>.yaml  # hand-assigned target priorities
│   │   ├── runs/<run_id>.json    # tuning + judge results
│   │   └── tuned_weights.yaml    # output of the tuning command (consumed by consolidation)
│   └── prompts/                  # versioned prompt templates
│       ├── summarize_repo.md
│       ├── discover_taxonomy.md
│       ├── extract_requirements.md
│       ├── extract_interactions.md
│       ├── extract_domains.md
│       ├── group_requirements.md
│       ├── reconcile_group.md
│       ├── assess_criticality.md
│       ├── verify_cross_cluster_conflict.md
│       ├── label_cluster.md
│       └── judges/               # judge prompts (LLM-as-judge for evals and calibration)
│           ├── judge_summarize_repo.md
│           ├── judge_extract_requirements.md
│           └── judge_calibration.md
│
├── models/                       # vendored model artifacts for reproducibility
│   └── embeddings/
│       └── nomic-embed-text-v1.5.Q8_0.gguf  # pinned by HF revision SHA
│
├── evidence/                     # LAYER 1: immutable raw ingested data
│   ├── git/<repo>/...
│   ├── jira/<project>/<ticket>.md
│   ├── spreadsheets/<name>.csv
│   ├── rfp/<doc>.md
│   └── transcripts/<name>-<date>.md
│
├── normalized/                   # LAYER 2: uniform shape
│   └── <source_type>/
│       ├── <source_id>.md                  # the normalized document
│       └── <source_id>.embedding.json      # sidecar embedding (cached on content_hash)
│
├── cross_cluster/                # STAGE 4.5: cross-cluster reconciliation outputs
│   ├── candidates.json           # candidate pairs after embedding pre-filtering
│   └── conflicts.json            # verified cross-cluster conflicts (top-level artifact)
│
├── reports/                      # STAGE 5.5: timestamped consultant-facing reports
│   └── <ISO_timestamp>.md        # one report per `report` invocation; never overwritten
│
├── taxonomy/                     # STAGE 1.5: discovery iterations + proposal
│   ├── iterations/
│   │   └── <source_type>/
│   │       └── iter-<NN>.json    # one record per sampled doc per iteration
│   ├── findings.json             # consolidated findings across all source types
│   └── proposal.md               # human-reviewable proposal (diff vs starting taxonomy)
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
│       │   ├── review_queue.json
│       │   └── cross_cluster_annotations.json  # sidecar: links to cross_cluster/conflicts.json
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
# Optional: present only for source_type=git
normalization_kind: curated_summary   # vs raw_text (the default for other sources)
extra:
  # source-specific metadata
  jira_status: done
  jira_reporter: alice@example.com
---

<markdown body>
```

**`normalization_kind`** distinguishes documents that are direct renderings of their evidence (`raw_text`, the default — Jira tickets, RFPs, transcripts, spreadsheets) from documents that are **curated summaries** of larger evidence (`curated_summary` — currently only git repos; see [D-22]). Downstream stages MAY use this flag when they need to know whether to consult the underlying `evidence/` for additional detail.

#### RepoSummary (the body of normalized git docs)

When `source_type: git`, the normalized markdown body follows a fixed-section template. The template is the contract; the LLM that produces it has freedom within each section but MUST emit all sections.

```markdown
# <repo-name>

## Purpose
<1–3 sentences: what business or technical capability does this repo provide?>

## Public API Surface
<HTTP endpoints, event topics published/subscribed, CLI commands, library exports.
 List form. Empty section header allowed if genuinely none, with explicit "(none observed)".>

## Runtime Dependencies
<External services this repo depends on at runtime: databases, queues, third-party APIs,
 other repos in this assessment. List form with one line per dependency.>

## Primary Domain Concepts
<5–15 named concepts the repo organizes itself around. Mix of business and technical
 concepts is fine; this feeds domain extraction and cluster labeling.>

## Notes
<Anything notable that doesn't fit above: deprecation status, ongoing migrations,
 known architectural patterns (microservice, monolith, batch job, etc.).>
```

The git adapter:
1. Clones the repo into `evidence/git/<repo>/`.
2. Constructs an LLM prompt from: README files, top-level directory listing, recently modified files, package/build manifests, and any `*.md` docs at the repo root or in `docs/`.
3. Calls the `summarize_repo` prompt (cached on `hash(prompt + repo_content_hash + model)`, where `repo_content_hash` is over the prompt-input set, not the entire repo).
4. Writes the result to `normalized/git/<repo>.md` with `normalization_kind: curated_summary`.

The raw repo content stays in `evidence/git/<repo>/` and is available to extractors that need code-level detail (see [D-23]).

#### Embedding (sidecar at `normalized/<source>/<id>.embedding.json`)

```json
{
  "source_type": "jira",
  "source_id": "PROJ-123",
  "content_hash": "<NormalizedDoc.content_hash>",
  "embedding_model": {
    "name": "nomic-embed-text-v1.5",
    "revision": "<HF commit SHA>",
    "quant": "Q8_0",
    "dimension": 768
  },
  "prefix_applied": "clustering: ",
  "vector": [0.0123, -0.0456, ...],
  "embedded_at": "<ISO timestamp>"
}
```

**Cache behavior.** The embedding sidecar is re-computed when any of `content_hash`, `embedding_model.name`, `embedding_model.revision`, or `prefix_applied` changes. Otherwise it is reused. Stage 3a reads embeddings from these sidecars; it does not call the embedding model when sidecars are current.

**Prefix convention.** Embedding models in the Nomic family require task-specific prefixes (e.g., `search_document: `, `clustering: `). The embedding wrapper SHALL apply the prefix appropriate to the task (always `clustering: ` for Stage 3 use); the applied prefix is recorded in `prefix_applied` so divergence is detectable. Other model families that don't use prefixes record `prefix_applied: ""`.

#### Starting and Locked Taxonomy (in `config/taxonomy.{starting,locked}.yaml`)

The starting taxonomy mirrors the enum values defined elsewhere in §2.3 (requirement `type` / `status`, interaction `kind` / `evidence_strength`, domain `kind`). It is the **floor**: Stage 1.5 may add, refine, or split values, but removals require human approval in the proposal review.

```yaml
version: "<semver or hash>"
locked_at: <ISO timestamp; null in starting>
sources_used: [git, jira, rfp, spreadsheet, transcript]  # in locked only

requirement:
  type:
    - value: functional
      description: A behavior the system must perform.
    - value: quality_attribute
      description: A measurable property (performance, security, availability, ...).
    # ...
  status:
    - value: implemented
      description: Evidence shows it is in production.
    # ...

interaction:
  kind:
    - value: http_call
      description: Synchronous HTTP/REST request, including GraphQL over HTTP.
    # ...
  evidence_strength:
    - value: observed
      description: Extracted from code, config, or specs that implement the interaction.
    # ...

domain:
  kind:
    - value: business_domain
      description: A business capability or problem area.
    - value: technical_domain
      description: An implementation-side area or concern.
```

The **locked** taxonomy is the artifact downstream stages consume. The starting taxonomy stays in git as the prior; the locked taxonomy is the prior plus discovery findings, reviewed and accepted.

#### TaxonomyFinding (entry in `taxonomy/iterations/.../iter-NN.json`)

One record per sampled document per iteration. Captures what the discovery LLM saw and proposed for that document.

```json
{
  "iteration": 3,
  "source_type": "jira",
  "source_id": "PROJ-1287",
  "sampled_for": "diversity_axes_satisfied",
  "diversity_axes": {"size": "large", "age": "old", "structure": "many_comments"},
  "observations": {
    "requirement_type": {
      "values_used": ["functional", "constraint"],
      "ambiguous": [
        {"existing": "constraint", "alternative": "assumption",
         "rationale": "Statement reads more like a stated belief than a hard constraint."}
      ],
      "missing": [
        {"proposed_value": "regulatory_constraint",
         "rationale": "Several statements distinguish regulatory requirements from technical constraints.",
         "example_excerpt": "..."}
      ]
    },
    "interaction_kind": { "values_used": [...], "ambiguous": [...], "missing": [...] },
    "domain_kind": { "...": "..." }
  },
  "advances_learning": true,
  "advance_reason": "Proposed new value 'regulatory_constraint' for requirement.type"
}
```

`advances_learning` is set per iteration based on the rule in [D-17]. The discovery loop terminates when this is `false` for two consecutive iterations per source type, or the per-source iteration cap is hit (whichever comes first).

#### Taxonomy Findings consolidated (in `taxonomy/findings.json`)

Aggregates all per-document findings into a single proposal-ready structure.

```json
{
  "schema_target": "requirement.type",
  "starting_values": ["functional", "quality_attribute", "constraint", "assumption", "change_plan"],
  "proposed_additions": [
    {
      "value": "regulatory_constraint",
      "rationale": "<merged across sources>",
      "supporting_findings": ["jira:PROJ-1287:iter-3", "rfp:doc-12:iter-1"],
      "confidence": "high"
    }
  ],
  "proposed_refinements": [
    {
      "value": "quality_attribute",
      "current_description": "A measurable property...",
      "proposed_description": "...",
      "rationale": "Sources consistently describe quality attributes with explicit thresholds; description should reflect that."
    }
  ],
  "proposed_removals": [
    {
      "value": "assumption",
      "rationale": "Not used in any sampled document.",
      "supporting_findings": [],
      "requires_human_approval": true
    }
  ],
  "ambiguities": [
    {
      "between": ["constraint", "assumption"],
      "occurrences": 7,
      "guidance_proposal": "Add to prompt: constraints are external/binding; assumptions are stated beliefs."
    }
  ]
}
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

#### Clustering configuration (in `config/clustering.yaml`)

All structural-phase parameters live here. Changes invalidate cluster assignments via the assignment cache.

```yaml
version: "<semver or hash>"

embedding:
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

#### Cluster entry (in `clusters/_index.yaml`)

```yaml
- name: payments-service
  path: clusters/payments-service
  parent: clusters/financial-domain   # null if root
  archived: false
  archived_at: null                   # ISO timestamp when archived: true was set; null otherwise
  archived_at_versions:                # captured at archival time; null otherwise; see [D-49]
    consolidation_config: null         # config/consolidation.yaml version at archive time
    clustering_config: null            # config/clustering.yaml version at archive time
    taxonomy: null                     # config/taxonomy.locked.yaml version at archive time
  member_count: 47
  summary_hash: <hash of summary inputs>   # cache key
  seeded_from: git:payments-service        # provenance of cluster creation
  origin: seed | orphan                    # seed = git-derived; orphan = HDBSCAN-discovered
```

**Archival semantics ([D-49] through [D-52]):**
- `archived: true` is set manually by the consultant editing `_index.yaml`. No automation.
- When transitioning from `false` to `true`, the consultant SHOULD populate `archived_at` and `archived_at_versions` (the spec doesn't enforce, but the report won't render archive-state information cleanly without them).
- Member docs (listed in `clusters/<name>/members.yaml`) remain members; they are NOT released to the unassigned pool.
- Cluster files (`summary.md`, `members.yaml`, `consolidated/*.json`, `consolidated/cross_cluster_annotations.json`) remain in place and readable. They are frozen at archive-time state.
- Stages that produce outputs from clusters (3b labeling, 4 consolidation, 4.5 cross-cluster, 5.5 report's landscape) read the `archived` flag and skip archived clusters per [D-51].
- Unarchival is just setting `archived: false`; next pipeline run resumes processing. `archived_at_versions` is preserved as historical record of the archival episode.

#### Cluster assignment record (in `clusters/_assignments.json`)

The structural phase's output. Read by phase 3b and downstream stages; written only by Stage 3a.

```json
{
  "clustering_version": "<config/clustering.yaml version>",
  "embedding_version": "<embedding.name>@<embedding.revision>",
  "assignments": [
    {
      "source_type": "jira",
      "source_id": "PROJ-123",
      "cluster_path": "clusters/payments-service",
      "similarity": 0.71,
      "low_confidence": false,
      "method": "nearest_seed | hdbscan_orphan | manual_override"
    }
  ],
  "unassigned": [
    {"source_type": "transcript", "source_id": "kickoff-2026-03-14",
     "best_similarity": 0.42, "reason": "below_threshold_no_orphan_cluster"}
  ]
}
```

#### Consolidation configuration (in `config/consolidation.yaml`)

All knobs that affect grouping, reconciliation, and scoring live here. Changes invalidate consolidation outputs via the consolidation cache.

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
  git: 0.8                         # code is strong evidence of what IS, less so of what SHOULD BE
  transcript: 0.4

reconciliation:
  rules:
    # Applied in order; first match wins.
    - manual_override                # explicit in config/consolidation_overrides/<group_id>.yaml
    - source_authority               # higher weight wins
    - recency                        # newer source_date wins
    - llm_judgment                   # fallback; rationale always recorded

confidence:
  # Weights for the deterministic formula. Tunable via calibration.
  weights:
    source_count: 0.20               # log-scaled; more sources = more confidence
    authority_weighted_agreement: 0.35  # weighted agreement across sources
    recency_spread_penalty: 0.10     # large spread → less confident
    statement_similarity: 0.15       # high similarity within group → less interpretation needed
    conflict_penalty: 0.20           # presence of conflict reduces confidence
  # Defaults are overridden by config/calibration/tuned_weights.yaml when present.

criticality:
  # LLM-emitted on a fixed discrete scale.
  scale: [critical, important, moderate, minor]
  # Mapping to numeric values used in review_priority computation:
  numeric:
    critical: 1.00
    important: 0.70
    moderate: 0.40
    minor: 0.15

review_priority:
  # The final ordering signal. Formula is tunable but defaults to:
  formula: "criticality_numeric * (1 - confidence)"
  # Optional boosters (default off):
  change_plan_boost: 0.0             # add to priority when requirement.type == change_plan
  cross_cluster_boost: 0.20          # add to priority when item participates in a cross-cluster conflict; see [D-40]

cross_cluster:
  enabled: true                      # set false to skip Stage 4.5 entirely (cost-bounded runs)
  embedding_threshold: 0.85          # conservative; only highly-similar pairs get LLM verification
  detect_kinds: [contradiction, scope_mismatch]   # only these kinds; status/type/version excluded by [D-41]
  max_candidate_pairs: 500           # hard cap; if exceeded, halt and surface as a warning
  min_pair_cluster_distance: 1       # 1 = siblings or unrelated; 0 = same cluster (always excluded)
```

#### RequirementGroup (intermediate; in `clusters/<cluster>/consolidated/groups.json`)

Persisted between phases so reconciliation and scoring are independently inspectable.

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

When the LLM verdict is `split`, one input group produces multiple output groups; when `reject`, the candidate group is dissolved and members fall back to singleton groups.

#### Conflict (embedded in `ConsolidatedRequirement.conflict`)

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

**Conflict kinds:**
- `contradiction` — Two sources directly disagree on what the system must (not) do. Detectable by LLM; sometimes by negation patterns.
- `scope_mismatch` — Sources agree on the behavior but disagree on scope ("all customers" vs "EU customers"). Detectable by LLM.
- `status_disagreement` — Sources disagree on implementation status (code shows implemented; backlog has it as planned). Detectable deterministically from `status` fields.
- `version_skew` — Same requirement at different times with semantically different content (recency-driven). Detectable deterministically from `source_date` spread + LLM verification.
- `type_disagreement` — Sources classify the same requirement differently (functional vs constraint). Detectable deterministically from `type` fields.

#### Confidence (embedded in `ConsolidatedRequirement.confidence`)

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
  "weights_version": "<config/calibration/tuned_weights.yaml version or 'defaults'>",
  "formula_version": "<config/consolidation.yaml version>"
}
```

Confidence is a **deterministic** function of `signals` and `weights`. The same inputs always produce the same score. The LLM is not consulted for the score itself; it is consulted only for the qualitative parts of `Conflict` (description, resolution rationale).

#### Criticality (embedded in `ConsolidatedRequirement.criticality`)

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

Criticality is emitted by the LLM with the cluster summary as context, on the fixed discrete scale defined in `config/consolidation.yaml`. The `numeric` value is derived from the discrete `level` via the same config (not LLM-emitted). Cached on `hash(statement + cluster_summary_hash + prompt_version + model)`.

#### ConsolidatedRequirement (in `clusters/<cluster>/consolidated/requirements.json`)

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
  "change_plan_flag": true,           // convenience: any source had type=change_plan or status=planned/proposed

  "confidence": { "...": "<Confidence>" },
  "criticality": { "...": "<Criticality>" },
  "review_priority": 0.42,            // derived per config/consolidation.yaml formula

  "resolved_by": {
    "model": "<pinned reasoning model>",
    "prompt_version": "<hash>"
  }
}
```

Resolution rules:
- `statement` is the canonical resolved text. If a single source dominated (per reconciliation rules), it's that source's statement (verbatim or lightly normalized); if the LLM produced a synthesis, the synthesis text and its provenance are recorded under the relevant `Conflict.resolution`.
- `type` and `status` are **single resolved values**. Disagreement among sources surfaces in `conflicts[]` with kinds `type_disagreement` or `status_disagreement` — the resolved value is in the top-level fields; the disagreement remains visible.
- `change_plan_flag` is a derived convenience flag, true when any contributing requirement had `type: change_plan` OR `status: planned | proposed`. The review queue treats this flag as a tagging signal (see [D-37]).

#### CalibrationCase (in `config/calibration/cases/<case_id>.yaml`)

One file per calibration case. Captures a hand-assigned **target priority** for a specific consolidated requirement, used to tune confidence weights and validate criticality assessment.

```yaml
case_id: cal-payments-001
case_kind: priority_ranking | scoring_check
added_at: 2026-04-22
added_by: manual_curation

frozen_input:
  cluster_summary: |
    <verbatim cluster summary at time of authoring>
  consolidated_requirement:
    # frozen copy of the ConsolidatedRequirement (or a candidate produced for this case)
    statement: "..."
    type: functional
    status: planned
    sources: [...]
    conflicts: [...]

target:
  # The consultant's hand-judged correct outcome.
  criticality_level: critical
  # Optional: target confidence band (rarely needed; usually we tune via priority).
  expected_confidence_band: [0.4, 0.6]
  # Required: target review_priority rank position (within the calibration set).
  target_rank: 3
  notes: |
    Regulatory requirement; high impact if missed. Multiple sources but with stale RFP language.

rubric:
  # Used by the calibration judge.
  criteria:
    - name: priority_alignment
      description: "Computed review_priority places this case within ±2 ranks of target_rank."
      weight: 0.5
    - name: criticality_alignment
      description: "Computed criticality_level matches target_level."
      weight: 0.3
    - name: confidence_plausibility
      description: "Computed confidence is within the target band (if specified)."
      weight: 0.2
```

#### CalibrationRun (in `config/calibration/runs/<run_id>.json`)

```json
{
  "run_id": "2026-05-14T11-00-00Z",
  "consolidation_config_version": "<config/consolidation.yaml version>",
  "weights_tested": {
    "source_count": 0.20, "authority_weighted_agreement": 0.35, "...": "..."
  },
  "cases": [
    {
      "case_id": "cal-payments-001",
      "computed": {
        "criticality_level": "critical",
        "confidence_score": 0.51,
        "review_priority": 0.49,
        "rank_in_set": 3
      },
      "judge_verdict": { "...": "<JudgeVerdict against rubric>" },
      "case_outcome": "pass | fail | borderline"
    }
  ],
  "aggregate": {
    "mean_score": 0.78,
    "rank_correlation": 0.83,
    "n_pass": 42, "n_fail": 4, "n_borderline": 4
  },
  "verdict": "pass | fail | tuning_proposed"
}
```

When `verdict: tuning_proposed`, the calibration command additionally writes proposed weight adjustments to `config/calibration/tuned_weights.yaml` for human review. Like the taxonomy lock ([D-20]), tuning is a human-gated step: the consultant reviews proposed weights and explicitly accepts them.

#### CrossClusterCandidate (in `cross_cluster/candidates.json`)

Intermediate output of Stage 4.5's embedding pre-filtering. Persisted for inspectability and cache reuse.

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
  "cluster_distance": 2,           // tree distance; 1 = siblings, 2 = aunt/uncle, etc.
  "verified": false                // becomes true after LLM verification produces a verdict
}
```

#### CrossClusterConflict (in `cross_cluster/conflicts.json`)

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
  "verdict": "confirmed_conflict",     // confirmed_conflict | not_a_conflict | needs_review
  "verdict_rationale": "<one-paragraph LLM explanation>",
  "detected_by": {
    "model": "<pinned reasoning model>",
    "prompt_version": "<hash>"
  }
}
```

Stage 4.5 emits one record per LLM-verified candidate. `verdict: not_a_conflict` entries are kept (not deleted) so re-runs don't re-pay for verifying the same negative cases.

#### CrossClusterAnnotation (in `clusters/<cluster>/consolidated/cross_cluster_annotations.json`)

Sidecar file written by Stage 4.5 that links per-cluster `ConsolidatedRequirement` records to their cross-cluster conflict participations. **Preserves immutability of Stage 4 outputs** (§1 principle 2): per-cluster `requirements.json` is not modified. Downstream consumers (review queue generation, report) read both files together.

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

#### ReviewQueueItem (in `review_queue.json`)

A flat sortable list, sorted descending by `review_priority`. Same shape as `ConsolidatedRequirement` plus location and a short tag set for filtering. Cross-cluster conflicts and the `cross_cluster_boost` are folded in here at queue-generation time.

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
- `<conflict_kind>` — one tag per distinct `conflict.kind` present (e.g., `contradiction`, `scope_mismatch`).
- `low_confidence` — `confidence.score < 0.4`.
- `borderline_criticality` — criticality is within the borderline band defined in `config/consolidation.yaml`.
- `singleton` — group has exactly one source (no cross-source corroboration).
- `cross_cluster_conflict` — item participates in at least one verified `CrossClusterConflict` (`verdict: confirmed_conflict`).

#### Report configuration (in `config/report.yaml`)

Controls what the report includes and how freshness is judged. Lives in version control.

```yaml
version: "<semver or hash>"

top_queue:
  size: 50                            # number of review queue items rendered in full

freshness:
  # A signal is "stale" when no run satisfying these conditions has occurred
  # against the current artifact versions. Used in the Health section.
  eval:
    require_pass_for_current_prompt: true   # eval must have passed for the current prompt_version
    max_age_days: null                       # null = no age cap; integer = warn if older
  calibration:
    max_age_days: 30                         # warn if last accepted calibration is older
    require_run_after_consolidation_config_change: true
  taxonomy:
    warn_if_locked_with_from_starting: true  # surface the [D-19] shortcut as a known limitation

sections:
  # Per-section toggle. All on by default. The order in the rendered report matches this list.
  - top_queue
  - landscape
  - health
  - provenance

provenance:
  per_source_breakdown: true            # show counts by source_type as well as totals

health:
  show_model_pins: true                 # surface config/models.yaml versions
  show_prompt_versions: true            # surface prompt hashes for each LLM-driven step
```

#### ReportRun (header block written into each `reports/<timestamp>.md`)

Every report opens with a YAML frontmatter block capturing the inputs that produced it. This makes any rendered report self-describing and diffable.

```yaml
---
report_id: 2026-05-14T14-30-00Z
report_config_version: <config/report.yaml version>

inputs:
  taxonomy:
    version: <config/taxonomy.locked.yaml version>
    locked_at: <ISO>
    locked_from_starting: false
  clustering:
    version: <config/clustering.yaml version>
    embedding_model: nomic-embed-text-v1.5@<revision>
  consolidation:
    version: <config/consolidation.yaml version>
    tuned_weights_version: <config/calibration/tuned_weights.yaml version or 'defaults'>
  cross_cluster:
    enabled: true
    candidates_count: 187
    confirmed_conflicts: 12
    needs_review: 3

freshness_warnings:
  # Populated when freshness signals indicate staleness; empty when clean.
  - id: eval_stale_extract_requirements
    severity: warn
    message: |
      Eval for extract_requirements has no passing run for current prompt
      version <hash>; most recent run is from 2026-05-02 against an older prompt.
  - id: calibration_stale
    severity: warn
    message: |
      Last accepted calibration is 47 days old (threshold: 30). Confidence
      weights may not reflect current consolidation behavior.

counts:
  evidence:
    git_repos: 23
    jira_tickets: 1842
    rfp_docs: 7
    spreadsheets: 4
    transcripts: 11
  normalized: 1887
  extracted:
    requirements: 4321
    interactions: 1209
    domains: 412
  clusters:
    total: 35
    active: 31
    archived: 4
  consolidated_requirements: 2876
  review_queue_total: 2876
  review_queue_rendered: 50
---
```

The frontmatter is followed by markdown body content (sections specified in §3 Stage 5.5).

#### Eval configuration (in `config/eval.yaml`)

Pins the judge model and per-extractor thresholds. Lives in version control; changes are reviewable.

```yaml
version: "<semver or hash>"

judge:
  model: <pinned model id, e.g. claude-sonnet-4-5-20250929>
  temperature: 0.0
  max_tokens: 2048

extractors:
  summarize_repo:
    style: llm_as_judge
    judge_prompt: judges/judge_summarize_repo.md
    thresholds:
      mean_score: 0.80          # 0..1 rubric score from judge
      min_score: 0.60           # no single case scores below this
    borderline_band: [0.65, 0.85]  # cases in this band require human review

  discover_taxonomy:
    style: fully_labeled
    thresholds:
      precision: 0.85
      recall: 0.85
    borderline_band: {precision: [0.80, 0.90], recall: [0.80, 0.90]}

  extract_requirements:
    style: llm_as_judge_plus_assertions
    judge_prompt: judges/judge_extract_requirements.md
    thresholds:
      mean_score: 0.75
      assertion_pass_rate: 1.0  # ALL assertions must pass
    borderline_band: [0.70, 0.85]

  extract_interactions:
    style: fully_labeled
    thresholds:
      kind_accuracy: 0.90
      participants_f1: 0.85
      endpoint_recall: 0.70
    borderline_band: {kind_accuracy: [0.85, 0.95]}

  extract_domains:
    style: assertions_only
    thresholds:
      assertion_pass_rate: 0.95
    borderline_band: [0.90, 1.0]
```

#### EvalCase (in `config/evals/<extractor>/cases/<case_id>.yaml`)

One file per eval case. Style is per-extractor (set in `config/eval.yaml`) and determines which fields are required.

```yaml
case_id: req-jira-PROJ-123
extractor: extract_requirements
source:
  source_type: jira
  source_id: PROJ-123
  # The case carries a frozen copy of the input so eval is reproducible even if
  # normalized/ is regenerated. Body is the NormalizedDoc body; frontmatter is
  # a subset relevant to the extractor.
  frozen_input:
    frontmatter:
      source_type: jira
      source_id: PROJ-123
      source_date: 2026-02-14
      content_hash: <sha256>
    body: |
      <verbatim normalized markdown body>

# For style: fully_labeled
expected_output:
  - id: PROJ-123:0
    statement: "..."
    type: functional
    status: planned
    # ...

# For style: assertions_only OR _plus_assertions
assertions:
  must_include:
    - description: "A requirement covering payment refund flow"
      check: "any requirement whose statement matches /refund/i AND type in [functional, change_plan]"
  must_not_include:
    - description: "No human-collaboration interactions"
      check: "no interaction with kind in [meeting, handoff]"

# For style: llm_as_judge OR _plus_assertions
rubric:
  # Sent to the judge along with the input and the candidate output.
  # The judge returns a structured score per criterion plus an overall score.
  criteria:
    - name: completeness
      description: "All clearly-stated requirements in the source are captured."
      weight: 0.4
    - name: faithfulness
      description: "No requirements are invented; every statement is supported by the source."
      weight: 0.4
    - name: classification
      description: "Type and status are reasonable given the source."
      weight: 0.2

# Optional: provenance for how this case got here
origin:
  added_at: 2026-03-12
  added_by: discovery_sample | manual_curation | regression_capture
  notes: "Seeded from taxonomy discovery iteration 3."
```

The `frozen_input` field is deliberate: it captures the exact bytes the extractor saw at the time the case was authored. If `normalized/` is later regenerated and the doc shifts, the eval case still tests the prompt against the same input.

#### JudgeVerdict (embedded in eval run records)

When `style` involves a judge, the judge returns structured output validated against this schema:

```json
{
  "case_id": "...",
  "criteria_scores": [
    {"name": "completeness", "score": 0.8, "rationale": "Missed the cancellation-refund variant."}
  ],
  "overall_score": 0.78,
  "borderline": true,
  "judge_model": "claude-sonnet-4-5-20260101",
  "judge_prompt_version": "<hash>"
}
```

The `borderline` flag is set by the eval runner (not the judge) based on `config/eval.yaml` borderline bands. The judge only scores.

#### EvalRun (in `config/evals/<extractor>/runs/<run_id>.json`)

One file per eval invocation. Captures inputs, outputs, judgments, and the pass/fail verdict.

```json
{
  "run_id": "2026-05-14T10-30-00Z",
  "extractor": "extract_requirements",
  "extractor_prompt_version": "<hash>",
  "extractor_model": "<pinned id>",
  "judge_model": "<pinned id>",
  "judge_prompt_version": "<hash>",
  "eval_config_version": "<config/eval.yaml version>",
  "cases": [
    {
      "case_id": "req-jira-PROJ-123",
      "actual_output": { "...": "..." },
      "assertion_results": [
        {"description": "...", "passed": true}
      ],
      "judge_verdict": { "...": "<JudgeVerdict>" },
      "case_outcome": "pass | fail | borderline"
    }
  ],
  "aggregate": {
    "mean_score": 0.82,
    "min_score": 0.61,
    "assertion_pass_rate": 1.0,
    "n_pass": 17,
    "n_fail": 1,
    "n_borderline": 2
  },
  "thresholds_applied": { "...": "<copied from config/eval.yaml at run time>" },
  "verdict": "pass | fail",
  "previous_run_id": "<prior run on same extractor, for diff reporting>"
}
```

The `verdict` is `pass` iff all configured thresholds are met AND zero cases are `fail`. Borderline cases do not block (per [D-30]) but are surfaced in the run report.

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

For most source types the normalized doc is a direct rendering of evidence (`normalization_kind: raw_text`). The **git adapter is special**: a repo is not a document, so the normalized doc is an **LLM-generated curated summary** following the `RepoSummary` template (§2.3), with `normalization_kind: curated_summary`. The raw repo content stays in `evidence/git/<repo>/` for later use by extractors that need code-level detail. See [D-22] and [D-23].

Adapters in scope for v1: `git`, `jira`, `spreadsheet`, `rfp`, `transcript`. Adding a new source type means writing one adapter; nothing downstream changes.

**Key decisions.** [D-1 Filesystem-as-DB], [D-2 Uniform doc shape], [D-3 Adapter pattern], [D-22 Git-repo curated summary], [D-23 Raw evidence accessible to extractors].

**Failure modes.**
- Lossy normalization (e.g., spreadsheets with rich formatting flattened too aggressively).
- Stale `evidence/` if upstream changed but our cache says "fetched recently."
- Spreadsheets and RFPs that defy markdown conversion (large tables, embedded images).
- Jira tickets with thousands of comments blowing past context windows in later stages.
- **Repo-summary blind spots.** The git adapter's prompt input (README, top-level structure, manifests, `docs/`) may miss what makes a repo distinctive (e.g., logic buried in a non-obvious module). Mitigation: the `Notes` section of the template explicitly invites the LLM to flag uncertainty; eval set for `summarize_repo` includes repos with non-obvious structure.
- **Empty-section drift.** LLM omits sections it deems empty. Mitigation: schema validation requires all template sections present; "(none observed)" is the explicit empty value.

### Stage 1.5 · Taxonomy Discovery

**Purpose.** Validate and refine the starting taxonomy against real evidence before bulk extraction locks in expensive token spend. Produce a locked taxonomy that downstream extractors consume.

**Input → Output.** `normalized/` + `config/taxonomy.starting.yaml` → `taxonomy/` + `config/taxonomy.locked.yaml`.

**When it runs.** Once per assessment, blocking. Stage 2 (Extract) refuses to run without `config/taxonomy.locked.yaml`. Re-running Stage 1.5 produces a new `taxonomy.locked.yaml` version; downstream stages with cached outputs based on the prior version are invalidated through normal cache-key versioning.

**Approach.** A bounded discovery loop per source type, followed by global consolidation and human-reviewed locking.

**1.5a · Stratified sampling, per source type.**
- For each source type in scope, repeatedly sample one `NormalizedDoc` until learning stalls.
- Sampling prioritizes **diversity axes**: size (small/medium/large), age (recent/median/old), structure (e.g., for Jira: bug/story/epic; for git: code/config/docs/specs), topic (clustered by embedding to spread coverage).
- Each iteration's pick maximizes a diversity score against previously-sampled docs in this source type. Ties broken by earliest age.
- Sampled docs are recorded; the same doc is not re-sampled within a source type.

**1.5b · Per-document finding extraction (LLM, cached).**
- For each sampled doc, run a single LLM call with the `discover_taxonomy` prompt and the **current starting taxonomy** as context.
- Output is a `TaxonomyFinding` (§2.3): which existing enum values applied, which were ambiguous (and against what alternative), which were missing (with proposed new value, rationale, supporting excerpt).
- Structured output via tool-calling; cached on `hash(prompt + doc_content_hash + current_taxonomy_hash + model)`.

**1.5c · Per-iteration learning evaluation.**
- An iteration **advances learning** if it introduces at least one of:
  - a new proposed enum value not seen in previous iterations of this source type;
  - a new ambiguity pair not seen previously;
  - a new gap report against an enum that previously showed no gaps.
- Repeated observation of an existing finding does **not** count as advancing learning, but increases its support count (used during consolidation).

**1.5d · Termination per source type.**
- The loop for a source type terminates when **two consecutive iterations do not advance learning**, OR when the **per-source iteration cap** is reached (default: 15 iterations; configurable in `models.yaml`).
- The cap is a belt-and-suspenders safety against pathological non-convergence on noisy sources.

**1.5e · Cross-source consolidation.**
- After all source types finish, all `TaxonomyFinding` records are aggregated into `taxonomy/findings.json` (§2.3).
- Findings are merged per schema target (e.g., `requirement.type`, `interaction.kind`).
- For each target, the script proposes: **additions** (new values with cross-source support), **refinements** (description tightening based on observed usage), **removals** (starting values never used — flagged as `requires_human_approval: true` per [D-18]), and **ambiguities** (pairs flagged repeatedly, with proposed prompt-level guidance).

**1.5f · Proposal generation.**
- A human-readable `taxonomy/proposal.md` is written, showing a diff vs. the starting taxonomy: what's added, refined, proposed-for-removal, and flagged-ambiguous, each with rationale and supporting excerpts (linked to the original sampled docs).
- The proposal is the review artifact. The consultant edits it (accepting, rejecting, or modifying proposals) and then runs the lock command.

**1.5g · Lock.**
- The lock command reads the (possibly edited) proposal and writes `config/taxonomy.locked.yaml`.
- Lock records: `version` (hash of content), `locked_at` (timestamp), `sources_used` (which source types contributed to discovery).
- After lock, downstream stages may proceed. Discovery iterations remain in `taxonomy/` as the audit trail of why the taxonomy looks the way it does.

**Key decisions.** [D-17 Bounded discovery termination], [D-18 Starting taxonomy as floor], [D-19 Stage 1.5 blocks Stage 2], [D-20 Human-reviewed lock].

**Failure modes.**
- **Sample-driven blindness.** A source type with few or quiet documents under-explores its taxonomy. Mitigation: starting taxonomy is a floor ([D-18]); removals require approval; consultant can see in the proposal which values had zero support and decide.
- **Discovery loop never terminates.** "Advances learning" is too lenient and every iteration finds *something*. Mitigation: hard iteration cap; "advance" requires *new* findings, not repeated ones.
- **Discovery overfits to LLM verbosity.** The discovery LLM is enthusiastic and proposes spurious new values. Mitigation: cross-source consolidation requires support from **at least two findings** for a proposed addition to reach "high confidence"; single-finding proposals are flagged "low confidence" in the proposal.
- **Taxonomy drift mid-assessment.** After lock, real extraction reveals genuine gaps. Mitigation: per [D-21], document as known limitation; finish the run; revisit only if severity warrants a re-lock. The cost of restarting is mostly cache-recoverable but prompt changes still invalidate extractor cache for affected sources.
- **Iteration cost.** Each iteration is a full-document LLM call. At ~15 iterations × 5 source types = ~75 calls on cheap model. Negligible. The expense is consultant review time, not tokens.

### Stage 2 · Extract

**Purpose.** Derive structured information of interest (requirements, interactions, domains) from normalized docs.

**Input → Output.** `normalized/` + `config/taxonomy.locked.yaml` → `extracted/`.

**Prerequisite.** `config/taxonomy.locked.yaml` MUST exist. Stage 2 refuses to run otherwise. The locked taxonomy supersedes the enum values defined in §2.3, which serve as the starting taxonomy (the floor).

**Approach.** Three source-agnostic extractors run independently per document:

1. **`extract_requirements`** — produces `Requirement` rows (§2.3). Captures `type` (functional / quality_attribute / constraint / assumption / change_plan) and `status` (implemented / planned / proposed / abandoned / unknown). Status MUST be set per source; the extractor uses `source_type` and source-specific cues as context to infer status (e.g., closed Jira ticket → likely `implemented` or `abandoned` depending on resolution; RFP statement → likely `proposed` or `planned`).

2. **`extract_interactions`** — produces `Interaction` rows (§2.3) for **runtime topology only**. Captures `kind`, `participants` (with explicit `bidirectional` flag when direction is unclear), `endpoint` (when available; degrades to service-level when not), and `evidence_strength` (observed / documented / inferred — see §2.3 for source-to-strength mapping). Human collaboration, team ownership, and build-time-only dependencies are **out of scope** and MUST NOT be emitted.

3. **`extract_domains`** — produces `Domain` rows (§2.3) of two kinds: `business_domain` and `technical_domain`. Both kinds may appear from the same source; the same concept may legitimately appear as both kinds with separate entries. Aliases are captured at extraction time to support consolidation merging.

Each extractor:
- Has its own prompt template in `config/prompts/`.
- Reads the full `NormalizedDoc`; `source_type` from the frontmatter is *context*, not *control flow*.
- Produces structured JSON via provider tool-calling, validated against the schema in §2.3.
- Has its own eval set ([D-6], [OPEN-2]).

Every extraction call goes through the LLM cache (Principle 3). Cache key: `hash(prompt_text + doc_content_hash + model_id + schema + locked_taxonomy_version)`. A new lock invalidates extraction cache automatically.

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

**Input → Output.** `normalized/` + `extracted/` + `config/clustering.yaml` → `clusters/`.

**Approach.** Four phases. The first is deterministic; the rest are LLM-driven but cached.

**3a · Structural (deterministic).**

Embedding (precondition):
- Every `NormalizedDoc` has a sidecar embedding (§2.3) computed with the pinned model from `config/clustering.yaml` and the `clustering: ` prefix.
- Stage 3a never calls the embedding model directly; it reads sidecars. If a sidecar is missing or stale (model revision mismatch, content_hash mismatch, prefix mismatch), Stage 3a triggers the embedding worker to refresh it.
- Embedding is one vector per `NormalizedDoc`. For git, that means the embedding represents the **curated repo summary** (§2.3 `RepoSummary`), not the raw repo — see [D-22].

Seeding:
- One cluster is seeded per non-archived git repo. Seed cluster name = repo name. `origin: seed`.
- Seed clusters are created before any assignment runs.

Assignment (non-git docs):
- For each non-git `NormalizedDoc`, compute cosine similarity against every seed cluster's embedding (the git repo summary's embedding).
- Assign to the nearest seed cluster IF `similarity ≥ similarity.assignment_threshold` (default 0.60, see [D-26]).
- If `similarity` falls within `low_confidence_band` (default [0.55, 0.65]), the assignment is recorded with `low_confidence: true` for human review.
- If `similarity < assignment_threshold`, the doc is **unassigned** at this step.

Orphan discovery (HDBSCAN on unassigned):
- Run HDBSCAN on the embeddings of all unassigned docs, with parameters from `config/clustering.yaml` (`min_cluster_size`, `min_samples`, `metric: cosine`, `random_seed: 42`).
- Each HDBSCAN cluster with ≥ `min_cluster_size` members becomes an orphan cluster (`origin: orphan`). Its name is a placeholder (`orphan-<index>`) until phase 3b labels it.
- HDBSCAN noise points (label `-1`) remain unassigned.

Output:
- `clusters/_index.yaml` updated with seed and orphan clusters.
- `clusters/_assignments.json` written with all assignments and the unassigned list (§2.3).
- `clusters/<cluster>/members.yaml` written per cluster.

Determinism guarantees:
- Same embeddings + same config = same assignments. HDBSCAN seed is fixed; assignment is a deterministic argmax with explicit tie-breaking on `source_id` lexicographic order.
- No LLM calls in phase 3a.

**3b · Semantic labeling (LLM, cached).**
- For each **non-archived** cluster, generate `summary.md` covering responsibilities and interactions, from member docs and their extractions.
- Archived clusters are skipped per [D-51]; their existing `summary.md` (frozen at archive-time state) remains untouched.
- Orphan clusters additionally get a meaningful name (replacing `orphan-<index>`) generated from their summary; the rename is recorded in `_index.yaml`.
- Cache key: `hash(sorted(member_content_hashes) + prompt_version + model)`.
- Summary only regenerates when membership or member content changes.

**3c · Hierarchy (LLM, low frequency).**
- `identifySuperClusters`: given **non-archived** sibling cluster summaries within a path, propose groupings.
- Archived clusters are not considered as super-cluster candidates and are not grouped into proposed parents.
- Output is a proposed tree edit applied to `_index.yaml`.
- Re-summarization of new parents cascades but is cached, so unchanged subtrees cost nothing.

**3d · Archival.**
- Manual flag in `_index.yaml`: the consultant sets `archived: true`, populates `archived_at` (ISO timestamp), and `archived_at_versions` (versions of relevant configs at archive time). No automation triggers archival ([D-50]).
- Member docs remain in `clusters/<name>/members.yaml` and are NOT released to the unassigned pool ([D-52]).
- All cluster files (`summary.md`, `members.yaml`, `consolidated/*.json`, `consolidated/cross_cluster_annotations.json`) remain in place, readable, and frozen at archive-time state.
- Archived git repos do NOT seed clusters in phase 3a re-runs.
- Unarchival is just flipping `archived: false`; processing resumes on the next pipeline run with `archived_at_versions` preserved as historical record.

**Re-clustering policy (see [D-28]).** Phase 3a operates in one of two modes set in `config/clustering.yaml`:
- `incremental` (default): existing assignments are preserved; only new or changed docs are assigned. New seed clusters are created when new non-archived git repos are added. HDBSCAN runs only over genuinely-new unassigned docs combined with already-unassigned docs. Stable cluster identities across runs.
- `full`: discard `_assignments.json`, re-run phase 3a from scratch. Embeddings are still cached; only assignment changes. Required when `assignment_threshold`, `embedding.revision`, or HDBSCAN params change.

The orchestration subcommand `cluster --full` forces a full re-cluster regardless of config.

**Key decisions.** [D-7 Embeddings-first clustering], [D-8 Git repos as seed], [D-9 Hash-keyed summary cache], [D-24 Local embedding model pinned + vendored], [D-25 Embedding sidecar files], [D-26 Single global threshold, manually tuned], [D-27 HDBSCAN over unassigned only], [D-28 Incremental clustering by default].

**Failure modes.**
- **Misfiled docs from embedding-only assignment.** A Jira ticket semantically near repo A but actually about repo B. Mitigation: low-confidence band surfaces borderline cases; explicit hints in normalized frontmatter (e.g., Jira `component` → repo mapping) can be honored by the adapter through an `assignment_hint` field that overrides automatic assignment (recorded with `method: manual_override`).
- **Bad repo-summary degrades clustering quality.** Since git repos are seeds, a misleading summary contaminates every assignment to that cluster. Mitigation: eval set for `summarize_repo`; consultant can manually edit `normalized/git/<repo>.md` after Ingest and the embedding refreshes on next run.
- **Super-cluster proposals that over-merge unrelated subsystems.** Mitigation: human review at hierarchy phase; conservative thresholds.
- **Embedding model drift between runs.** Two runs with different model revisions produce incomparable embeddings. Mitigation: `config/clustering.yaml` pins the revision and expected SHA-256; embedding sidecars record their model revision so mismatches are detectable and trigger refresh.
- **Threshold mis-tuning.** Too high → many unassigned docs and noisy orphan clusters; too low → everything assigned to nearest seed regardless of fit. Mitigation: low-confidence band surfaces borderline assignments; threshold tuning is documented as part of first-run validation.
- **HDBSCAN sensitivity.** Small `min_cluster_size` produces fragmented orphans; large values miss legitimate small subsystems. Defaults (3, 2) are tuned for medium-scale assessments and are adjustable in config.
- **Incremental drift.** Long-running incremental clustering can accumulate suboptimal assignments as the corpus grows. Mitigation: periodic `cluster --full` re-runs (cheap because embeddings stay cached).

### Stage 4 · Consolidate

**Purpose.** Group extracted requirements per cluster, surface and resolve conflicts with explicit kinds, and score for human review priority. Produce a ranked review queue.

**Input → Output.** `clusters/` + `extracted/` + `config/consolidation.yaml` + (optional) `config/calibration/tuned_weights.yaml` → `clusters/**/consolidated/` + `review_queue.json`.

**Approach.** Runs **bottom-up** through the cluster tree. At each non-archived cluster, six phases execute in sequence; child-cluster outputs propagate upward as inputs.

**4a · Gather.**
- Iterate over **non-archived** clusters only ([D-51]). Archived clusters are skipped entirely at this stage.
- For each non-archived cluster, collect all `Requirement` records from member docs (via `extracted/<source_type>/<source_id>/requirements.json`).
- Collect already-consolidated requirements from **non-archived** child clusters (each propagates upward as a single record carrying its own `sources` and `conflicts`). If a child cluster is archived, its consolidated outputs are NOT propagated to the parent — they're frozen, not feeding active processing.

**4b · Group (two-stage; [D-34]).**

Pre-grouping (deterministic):
- Each requirement gets an embedding via the same wrapper used by clustering ([D-25]), with the `clustering: ` prefix replaced by a `grouping: ` prefix (recorded in the embedding sidecar). Embeddings are content-hash cached.
- Compute pairwise cosine similarity within the cluster's requirement set; build candidate groups as connected components where every edge ≥ `grouping.embedding_threshold` (default 0.78).
- Singletons (requirements with no above-threshold neighbors) become singleton candidates.

LLM verification:
- For each multi-member candidate group, call the `group_requirements` prompt with the member statements and source metadata. The LLM returns one of: `confirm`, `split` (with proposed sub-grouping), `reject` (members are unrelated).
- `split` produces multiple output groups; `reject` dissolves to singletons.
- Verification call cached on `hash(sorted(member_content_hashes) + prompt_version + model)`.
- `config/consolidation.yaml: grouping.llm_verification: false` is an escape hatch that skips verification and uses pre-groups directly (useful for cost-bounded re-runs; recorded in group provenance).

Output: `clusters/<cluster>/consolidated/groups.json` with one `RequirementGroup` record per group.

**4c · Conflict detection ([D-35]).**

Per group, detect all applicable conflict kinds:

- **Deterministic detections** (cheap, run first):
  - `status_disagreement`: members have ≥2 distinct `status` values.
  - `type_disagreement`: members have ≥2 distinct `type` values.
  - `version_skew` (candidate): `source_date` spread exceeds a threshold (default 180 days) AND members have non-trivial statement variation.
- **LLM-driven detections** (called only when the group has ≥2 members):
  - `contradiction`: explicit negation or mutual exclusivity between statements.
  - `scope_mismatch`: agreement on behavior with disagreement on scope/applicability.
  - Confirms or rejects candidate `version_skew` cases.

A group can have multiple conflicts of different kinds. Each conflict carries explicit `evidence` (the contributing requirements with verbatim excerpts). LLM-driven detection is a single call per group with a structured-output schema enumerating all conflict kinds found; cached on group inputs.

**4d · Reconciliation ([D-10] retained; rule application formalized).**

For each group, produce the resolved `statement`, `type`, and `status`:
- Apply reconciliation rules in the order defined in `config/consolidation.yaml: reconciliation.rules`.
- `manual_override`: looks up `config/consolidation_overrides/<group_id>.yaml` if present; if so, the override's values are used and `applied_rule: manual_override` is recorded.
- `source_authority`: sources are weighted by `source_authority`; the highest-weighted source's values win. Ties fall through.
- `recency`: most recent `source_date` wins. Ties fall through.
- `llm_judgment`: final fallback. Single LLM call with the `reconcile_group` prompt, returning the resolved values and a rationale. Always records rationale via `Conflict.resolution.rationale`.

When the resolved `statement` is a synthesis (i.e., not verbatim from any single source), this is flagged in the resolution rationale and the synthesis is recorded as the `statement` while the original excerpts remain in `sources`.

**4e · Scoring.**

Confidence (deterministic; [D-36]):
- Compute the five signals from §2.3 `Confidence`:
  - `source_count` (log-scaled): `min(1.0, log(1 + n) / log(1 + 5))` — saturates around 5 sources.
  - `authority_weighted_agreement`: weighted fraction of sources whose statement/type/status matches the resolved values, weighted by `source_authority`.
  - `recency_spread_penalty`: `min(1.0, spread_days / 730)` — penalty saturates at 2 years.
  - `statement_similarity`: mean pairwise cosine similarity of member statements (from grouping embeddings; effectively free).
  - `conflict_penalty`: 1.0 if any `Conflict` is present, else 0.0.
- Combine via the weighted formula in `config/consolidation.yaml: confidence.weights` (overridden by `config/calibration/tuned_weights.yaml` when present):
  - `score = w_count * source_count + w_auth * authority_weighted_agreement + w_sim * statement_similarity - w_recency * recency_spread_penalty - w_conflict * conflict_penalty`
  - Clamped to [0, 1].
- Signals and weights are recorded in the `Confidence` object for full auditability.

Criticality (LLM, cached; [D-37]):
- Call the `assess_criticality` prompt with the resolved statement and the cluster's `summary.md` as context.
- The LLM emits one of `critical | important | moderate | minor` (the fixed scale) plus a one-sentence rationale.
- The numeric value is looked up from `config/consolidation.yaml: criticality.numeric`; the LLM does not emit floats.
- Cached on `hash(statement + cluster_summary_hash + prompt_version + model)`.

Review priority (deterministic):
- Computed from the formula in `config/consolidation.yaml: review_priority.formula`. Default: `criticality_numeric * (1 - confidence.score)` + optional `change_plan_boost`.
- The combination favors items that are both critical AND uncertain — exactly the cases worth a human's time.

**4f · Emit.**
- Write `clusters/<cluster>/consolidated/requirements.json` (list of `ConsolidatedRequirement`).
- Write `clusters/<cluster>/consolidated/review_queue.json` (cluster-local queue, sorted by `review_priority`).
- Propagate `ConsolidatedRequirement` records upward; the parent cluster's 4a `gather` will treat each as a single source.

After all clusters: merge all cluster-local queues into top-level `review_queue.json`, sorted by `review_priority` descending, with `tags` derived per §2.3.

**Caching.** Consolidation is cached at three levels:
- Group-level: grouping result cached on member content hashes + grouping config.
- Conflict-level: conflict detection cached on group inputs.
- Criticality-level: criticality cached on statement + cluster summary hash.
Re-running consolidation when nothing has changed is near-free; changing `config/consolidation.yaml` invalidates the relevant levels selectively (see [D-38]).

**Key decisions.** [D-10 Provenance-driven resolution], [D-11 Bottom-up consolidation], [D-13 Expensive model here], [D-34 Two-stage grouping], [D-35 Multiple conflict kinds with explicit detection], [D-36 Deterministic confidence; LLM only for qualitative parts], [D-37 Discrete criticality scale; cluster summary as context], [D-38 Layered consolidation caching], [D-39 Calibration loop with human-gated weight tuning].

**Failure modes.**
- **Cross-cluster conflicts missed at this stage.** Bottom-up consolidation only sees one subtree at a time; conflicts between distant branches are not detected here. Stage 4.5 (Cross-cluster Reconciliation) addresses this; see [D-40].
- **Grouping over-merges.** Embedding pre-grouping followed by LLM `confirm` can still merge requirements that share vocabulary but differ in scope. Mitigation: LLM verification's `split` outcome is the primary defense; `scope_mismatch` conflict detection catches surviving cases.
- **Grouping under-merges.** Paraphrased equivalents fall below the embedding threshold and never enter LLM verification. Partial mitigation: threshold defaults at 0.78 are tuned conservatively; lowering increases LLM verification cost but improves recall.
- **Criticality miscalibration on niche clusters.** A cluster with very narrow scope may have its critical items rated `moderate` because the LLM lacks domain context. Mitigation: `assess_criticality` prompt explicitly anchors to the cluster summary; the calibration loop ([D-39]) catches systematic miscalibration.
- **Confidence weights mis-tuned.** Default weights are guesses. Mitigation: the calibration loop produces `tuned_weights.yaml` from human-judged cases; weights only override defaults after explicit human acceptance ([D-39]).
- **LLM-emitted criticality drift across model versions.** A model upgrade can shift the distribution of criticality levels. Mitigation: criticality cache key includes the model id; the calibration set runs after model changes and surfaces drift.
- **Manual overrides go stale.** An override authored in iteration 3 may no longer match the resolved group in iteration 12 (membership changed). Mitigation: overrides are keyed on `group_id`, which is content-derived; when the group changes, the override stops matching and a warning is emitted.

### Stage 4.5 · Cross-cluster Reconciliation

**Purpose.** Detect conflicts between consolidated requirements that live in different cluster subtrees and never share a per-cluster consolidation pass. Surface findings without re-running per-cluster consolidation.

**Input → Output.** All `clusters/**/consolidated/requirements.json` (from Stage 4) + `config/consolidation.yaml` → `cross_cluster/candidates.json` + `cross_cluster/conflicts.json` + `clusters/**/consolidated/cross_cluster_annotations.json`.

**When it runs.** Always, immediately after Stage 4 in `consolidate` (per [D-43]). Can be skipped by setting `config/consolidation.yaml: cross_cluster.enabled: false` for cost-bounded runs.

**Scope by design ([D-41]):**
- Detects only `contradiction` and `scope_mismatch` kinds. `status_disagreement` and `type_disagreement` are excluded because same-named concepts in different clusters legitimately differ on these dimensions (a "user" in auth ≠ a "user" in analytics). `version_skew` is excluded because cross-cluster same-statement-different-time is unusual and noisy.
- Detects only between requirements in **different** clusters (`cluster_distance ≥ 1` from `config`). Same-cluster pairs were already handled in Stage 4b/c.

**Approach.** Four phases.

**4.5a · Embedding pre-filtering (deterministic).**
- Collect all `ConsolidatedRequirement` records from non-archived clusters into a global pool. Archived clusters are excluded per [D-51]; their consolidated requirements do not contribute to cross-cluster conflict candidates and cannot receive cross-cluster boosts.
- For each requirement, compute or reuse its embedding via the same wrapper used in Stage 4b (the `grouping: ` prefix), cached on content hash.
- Compute pairwise cosine similarity across the entire pool, but **exclude same-cluster pairs** and pairs whose `cluster_distance < min_pair_cluster_distance` (default 1).
- Retain pairs with `similarity ≥ cross_cluster.embedding_threshold` (default 0.85).
- If the candidate count exceeds `cross_cluster.max_candidate_pairs` (default 500), halt with a warning rather than proceeding silently — the consultant decides whether to raise the threshold or raise the cap.
- Write `cross_cluster/candidates.json` with all surviving pairs.

**4.5b · LLM verification.**
- For each candidate pair, call the `verify_cross_cluster_conflict` prompt with both consolidated requirements (statement, type, status, sources excerpts) and both cluster summaries as context.
- The LLM returns a structured `verdict: confirmed_conflict | not_a_conflict | needs_review`, the inferred `kind`, a description, and a rationale.
- `needs_review` is a deliberate third option for cases the LLM is uncertain about — surfaced for human judgment rather than forced into a binary.
- Cached on `hash(both consolidated_requirement_ids + both cluster_summary_hashes + prompt_version + model)`. Reusing two stable inputs means re-runs after consolidation changes only invalidate verifications that touch changed inputs.

**4.5c · Emit.**
- Write `cross_cluster/conflicts.json` with all verified records (including `not_a_conflict` and `needs_review` for cache persistence).
- For each `confirmed_conflict` and `needs_review`, write/update the relevant `clusters/<cluster>/consolidated/cross_cluster_annotations.json` sidecars referencing the conflict id.
- Per-cluster `requirements.json` is NOT modified — annotations live in sidecars to preserve immutability ([D-42]).

**4.5d · Review queue regeneration.**
- Top-level `review_queue.json` is regenerated to fold in cross-cluster annotations.
- For each `ReviewQueueItem` whose `consolidated_requirement_id` appears in any `confirmed_conflict`, apply `cross_cluster_boost` to `review_priority` (default 0.20, configurable).
- The `cross_cluster_conflicts` field on the item lists the relevant conflict ids; `tags` gains `cross_cluster_conflict`.
- `review_priority_components` breaks down the additive contributions so the boost is auditable.

**Key decisions.** [D-40 Stage 4.5 as separate phase; cross-cluster boost], [D-41 Conservative scope: contradiction and scope_mismatch only], [D-42 Annotations as sidecar files; immutability preserved], [D-43 Cross-cluster always runs, config-gated for cost], [D-44 Hard candidate cap with halt-and-warn].

**Failure modes.**
- **Candidate explosion.** A corpus with many similar-but-legitimately-distinct requirements (e.g., per-service variants of the same pattern) can produce thousands of candidates. Mitigation: hard cap ([D-44]) halts with a warning; the consultant raises the threshold or accepts a larger cap explicitly.
- **LLM verification false positives.** The verifier confirms a "conflict" that the per-cluster contexts make irrelevant. Mitigation: cluster summaries are part of the prompt; `needs_review` is a first-class verdict; the calibration loop ([D-39]) can include cross-cluster examples.
- **LLM verification false negatives.** The verifier rejects a real conflict (e.g., subtle scope mismatch). Mitigation: borderline cases that score in a `verdict: needs_review` band are surfaced; the consultant can override via the same `consolidation_overrides/` mechanism extended to cross-cluster ids.
- **Cross-cluster boost mis-tuned.** Default boost of 0.20 may push cross-cluster items above unrelated high-criticality items, or fail to surface them above noise. Mitigation: `cross_cluster_boost` is in `config/consolidation.yaml`; calibration cases can include cross-cluster examples and the boost is one more tunable weight.
- **Cluster reorganization invalidates cached verifications.** If a cluster splits or merges, consolidated requirement ids change, and verification cache entries are orphaned. Mitigation: cache keys include consolidated requirement ids (which are content-derived); orphan entries naturally stop being read. Cache cleanup is opportunistic.
- **Annotation sidecars go stale.** If Stage 4 re-runs and produces different consolidated requirements (different ids), Stage 4.5 annotations may reference ids that no longer exist. Mitigation: Stage 4.5 invalidates and rewrites annotation sidecars based on the current Stage 4 output; orphaned annotations are detected on read and ignored with a warning.

### Stage 5 · Orchestration

**Purpose.** Sequence stages with incremental, content-addressed execution.

**Approach.** Plain Python entrypoint, explicit subcommands:

```bash
python -m assessment ingest             # idempotent; only fetches changed sources; runs git repo summarization
python -m assessment taxonomy:discover  # runs Stage 1.5 discovery loop; writes taxonomy/proposal.md
python -m assessment taxonomy:lock      # reads (possibly edited) proposal; writes config/taxonomy.locked.yaml
python -m assessment eval <step>        # runs the eval set for a step; e.g. 'eval extract_requirements'
python -m assessment eval --all         # runs all configured eval sets; writes per-step run records
python -m assessment eval:seed <step>   # creates unlabeled EvalCase stubs from taxonomy discovery samples
python -m assessment extract            # refuses to run without locked taxonomy
python -m assessment embed              # refreshes stale embedding sidecars only; idempotent
python -m assessment cluster            # phases 3a-3d in current re-clustering mode (default: incremental)
python -m assessment cluster --full     # forces full re-cluster from scratch
python -m assessment consolidate        # Stage 4 (bottom-up) + Stage 4.5 (cross-cluster) + review_queue.json
python -m assessment consolidate --no-cross-cluster   # skips Stage 4.5; equivalent to cross_cluster.enabled=false
python -m assessment calibrate:run      # runs calibration cases against current weights; writes CalibrationRun + proposed weights
python -m assessment calibrate:accept   # accepts proposed weights into config/calibration/tuned_weights.yaml
python -m assessment report             # Stage 5.5: writes reports/<ISO_timestamp>.md
```

Discovery and lock are deliberately separate commands. `discover` is reproducible (caches its LLM calls); `lock` is a human-gated step.

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

### Stage 5.5 · Report

**Purpose.** Produce a consultant-facing "first read" markdown document that surfaces the highest-priority review items, the system landscape, the pipeline's health and freshness signals, and the provenance of the run. The report is the artifact the consultant opens to decide where to focus next.

**Input → Output.** All pipeline outputs (review queue, cluster index, cross-cluster conflicts, eval runs, calibration runs, config files) + `config/report.yaml` → `reports/<ISO_timestamp>.md`.

**When it runs.** On demand, by the consultant. Each invocation writes a new timestamped file; existing reports are never overwritten ([D-46]). Recommended cadence: after every consolidate run, plus an additional snapshot before major prompt or model changes for clean before/after comparison.

**Approach.** No LLM calls. The report is purely a rendering of existing artifacts; reproducibility comes from the frontmatter capturing every input version that contributed to the rendered content. Six concerns separated:

**5.5a · Frontmatter assembly.**
- Read versions from all config files (`taxonomy.locked.yaml`, `clustering.yaml`, `consolidation.yaml`, `calibration/tuned_weights.yaml` if present).
- Count artifacts: evidence per source type, normalized docs, extracted records per type, clusters, consolidated requirements.
- Read `cross_cluster/conflicts.json` for cross-cluster summary counts.
- Compute freshness signals (see 5.5d).
- Assemble the `ReportRun` YAML frontmatter (§2.3).

**5.5b · Top-N section (the headline).**
- Read `review_queue.json` (sorted by `review_priority` descending).
- Take the top `top_queue.size` items (default 50 per `config/report.yaml`).
- For each item, render a structured markdown block containing:
  - Cluster path and rank in queue.
  - Resolved statement, `type`, `status`, `change_plan_flag`.
  - All conflicts with kind, description, evidence excerpts.
  - Confidence breakdown: score + the five signals + which weights version produced it.
  - Criticality level + rationale (the LLM's one-sentence explanation).
  - `review_priority_components` (base + boosts + total) so the consultant sees exactly why this item ranked here.
  - Source provenance: one line per contributing source with type, id, date, and excerpt.
  - Cross-cluster references: links to other affected requirements when `cross_cluster_conflicts` is non-empty.
  - Tags as a compact filter line.

The block is self-contained — the consultant can act on a single item without opening other files.

**5.5c · Landscape section.**
- Read `clusters/_index.yaml` and per-cluster `summary.md` files.
- Render a tree view of the cluster hierarchy (depth-limited; archived clusters shown but **de-emphasized** — rendered with a visual marker like `[archived YYYY-MM-DD]` after the name and indented separately at the end of their parent's children).
- For each non-archived cluster, render: purpose (one line from summary.md), member count, top 3 domains (from extracted domains, deduplicated by alias), top 5 interactions (from extracted interactions, grouped by kind).
- For each archived cluster, render only: name, archive timestamp (from `archived_at`), member count, and the first line of its frozen `summary.md`. The full archived-cluster contents remain readable in `clusters/<name>/` for the consultant who needs them.
- This section is read-only orientation; no decisions hang on it.

**5.5d · Health section.**
- Compute freshness signals against `config/report.yaml: freshness`:
  - **Eval freshness:** for each LLM-driven step, check whether the most recent `EvalRun` was a `pass` against the current prompt version. If not, emit `eval_stale_<step>` warning.
  - **Calibration staleness:** check the age of the most recent `calibrate:accept` against `freshness.calibration.max_age_days`. Check whether any `consolidation.yaml` config change has happened since (via git history of the config file). Emit `calibration_stale` warning if either fails.
  - **Taxonomy freshness:** if `taxonomy.locked.yaml` was locked via the `--from-starting` shortcut ([D-19] escape hatch), emit `taxonomy_from_starting` warning.
  - **Model pin drift:** detect when any model id in `models.yaml` has a newer pinnable version available (best-effort; provider-dependent; non-blocking).
- Show pinned versions: every model id, every prompt version hash (per LLM-driven step), every config version.
- Warnings are written to frontmatter (`freshness_warnings`) AND surfaced in this section in human-readable form.

**5.5e · Provenance section.**
- Render counts from frontmatter as a clean table (per-source breakdown enabled by default per `config/report.yaml: provenance.per_source_breakdown`).
- Show ingestion timestamps for the most recently ingested artifact per source type.
- Report counts of active vs. archived clusters (e.g., "31 active clusters, 4 archived"). Detailed archive listings live in the Landscape section.
- Report the count of normalized docs that are members of archived clusters; this surfaces [R-27] (docs stuck in archived clusters) without requiring the consultant to grep.

**5.5f · Write.**
- Filename: `reports/<ISO_timestamp>.md` where `<ISO_timestamp>` is the report's `report_id` (UTC, filename-safe form, e.g. `2026-05-14T14-30-00Z`).
- Reports are never overwritten ([D-46]). Disk usage is a known concern; see [R-24].

**Key decisions.** [D-45 Report is a deterministic rendering; no LLM calls], [D-46 Always timestamped; never overwritten], [D-47 Freshness signals are first-class report content], [D-48 Section toggles via config; sections are independently authored].

**Failure modes.**
- **Missing inputs.** If `review_queue.json` doesn't exist (consolidate never ran), the report stage fails fast with a clear error rather than producing a half-empty report.
- **Stale references in rendered items.** A report rendered now references content_hashes that may change later. Acceptable: the frontmatter pins every input version, so the consultant can reason about what was true at report time even if subsequent edits change things.
- **Disk accumulation from never-overwritten reports.** Over many iterations, `reports/` grows unboundedly. Mitigation: consultants are encouraged to gitignore `reports/` for routine runs, committing only snapshots that matter (e.g., before major prompt changes); see [R-24].
- **Freshness false negatives.** A signal can be technically fresh (recent run) but semantically stale (the run was on a different corpus than now). Mitigation: the eval-pass check is tied to the current `prompt_version`, not just timestamp; calibration freshness is tied to consolidation-config-change detection via git history.
- **Freshness false positives.** A consultant who edited a prompt for a minor copy fix gets an eval-stale warning. Acceptable: the cost of a re-eval is low; the false positive is informative rather than blocking.

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
**Decision.** Each LLM-driven step has its own eval set under `config/evals/<step>/`. Five eval sets in v1: `summarize_repo`, `discover_taxonomy`, `extract_requirements`, `extract_interactions`, `extract_domains`. Each uses an evaluation style appropriate to its output shape, configured in `config/eval.yaml`. Eval is a separate command, run by the consultant before shipping prompt or model changes. Sets are seeded from taxonomy discovery samples and grown incrementally as regressions are caught. See [D-29], [D-30], [D-31], [D-32].
**Rationale.** Without eval sets, prompt changes are guesswork. Treating eval as a first-class artifact (with cases, runs, thresholds, and judge prompts under version control) is what makes the rest of the pipeline trustworthy.
**Alternatives.** Spot-checking. Trusts the LLM too much.
**Trade-offs.** Up-front labeling effort and ongoing maintenance. (Estimated 2–4 hours per eval set for the initial 15–20 cases; less for assertions-only style.)

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

### [D-17] Bounded taxonomy-discovery termination
**Decision.** Per-source-type discovery loop terminates on whichever comes first: (a) two consecutive iterations that do not "advance learning" (introduce a new proposed enum value, a new ambiguity pair, or a new gap report), or (b) a hard per-source iteration cap (default 15).
**Rationale.** "Iterate until stable" without a computable definition of stability doesn't terminate. Defining advancement as *new* findings, not repeated ones, gives a concrete rule. The cap is safety against pathological non-convergence on noisy sources.
**Alternatives.**
- Fixed iteration count per source (no stability check). Wastes calls on quickly-stable sources; under-samples noisy ones.
- Stop after N iterations with no advancement (N>2). Marginal benefit; usually one stale iteration is plenty.
- Vibes-based "looks stable to me." Not reproducible; rejected by [D-14].
**Trade-offs.** A source type with subtle late-emerging variants may be cut off by the cap. The cap is configurable in `models.yaml`; raising it costs more discovery calls but doesn't affect extraction.

### [D-18] Starting taxonomy is a floor; removals require human approval
**Decision.** `config/taxonomy.starting.yaml` (the enums defined in §2.3) is the floor for discovery. Discovery may add values, refine descriptions, propose removals, and flag ambiguities. **Removals are flagged in the proposal with `requires_human_approval: true` and are not applied silently.**
**Rationale.** A quiet sample (a source type with no `assumption`-flavored statements, say) should not erase a legitimate enum value. The starting taxonomy reflects thought already invested; discovery refines it, doesn't reset it.
**Alternatives.**
- Free-form discovery starting from zero. Rejected: throws away prior thought; sample-driven blindness becomes severe.
- Discovery as suggestion-only with no auto-application. Rejected: loses the value of automated finding aggregation; every change requires manual reconciliation.
**Trade-offs.** Legitimately obsolete enum values stay in the taxonomy until the consultant explicitly removes them in proposal review. Acceptable: one review step versus systematic over-pruning.

### [D-19] Taxonomy Discovery blocks Extract
**Decision.** Stage 1.5 runs once per assessment and produces `config/taxonomy.locked.yaml`. Stage 2 (Extract) refuses to run without it. Re-running Stage 1.5 produces a new locked version, which invalidates extraction caches via the extractor cache key.
**Rationale.** "Pay the cost up front." Locking before bulk extraction prevents the worse failure mode of finding taxonomy gaps after thousands of extracted records exist with stale enum values. Cache-key versioning means a re-lock cleanly invalidates affected work.
**Alternatives.**
- Discovery as a side-script, optional. Rejected: easy to skip; reproducibility suffers.
- Discovery as a sub-step inside Stage 2. Rejected: couples concerns; harder to reason about cache invalidation.
**Trade-offs.** Adds one stage and one blocking review step to the pipeline. Acceptable cost for the reliability gain. A consultant who wants to iterate fast can keep using the starting taxonomy by running `taxonomy:lock` immediately without discovery (`taxonomy:lock --from-starting`); this is recorded explicitly in the lock metadata as a known shortcut.

### [D-20] Human-reviewed lock via diff proposal
**Decision.** Discovery output is a human-readable `taxonomy/proposal.md` showing a diff vs. the starting taxonomy. The consultant reviews, edits if needed, then runs `taxonomy:lock` to write `config/taxonomy.locked.yaml`. No interactive prompts; no auto-lock.
**Rationale.** Reviewable, diffable, reproducible. Interactive prompts aren't reproducible (no record of what was accepted and why). Auto-lock skips the deliberate checkpoint that justifies the up-front cost of running discovery at all.
**Alternatives.**
- Interactive Y/N prompts in the script. Rejected: not reproducible; no audit trail.
- Auto-lock with after-the-fact edits to `taxonomy.locked.yaml`. Rejected: loses the deliberate review step; encourages drift.
**Trade-offs.** Requires the consultant to actually do the review. Mitigated by making the proposal scannable and pre-categorized (high vs. low confidence, supported vs. single-source).

### [D-21] Taxonomy debt found post-lock is documented, not chased
**Decision.** If extraction reveals genuine taxonomy gaps after lock, the gap is documented as a known limitation. The run finishes. Re-lock + re-extraction is only triggered if the severity (impact on the review queue) warrants it, judged by the consultant.
**Rationale.** Discovery is a sample-based prior; perfect coverage is not the goal. Restarting extraction on every minor finding produces diminishing returns and inflates costs. The consultant is the right decision-maker for severity.
**Alternatives.**
- Auto-restart on any post-lock taxonomy gap. Rejected: too aggressive; inflates cost.
- No documentation of gaps at all. Rejected: loses audit trail; future re-runs lose context.
**Trade-offs.** The final review queue may carry items with sub-optimal `type` or `kind` classifications. Acceptable: the underlying statements and provenance are intact; classification is a navigational aid, not the substance.

### [D-22] Git-repo normalization is an LLM-generated curated summary
**Decision.** The git adapter does not produce a "raw text dump" normalized doc. Instead, it produces a fixed-template `RepoSummary` (§2.3) generated by the `summarize_repo` LLM prompt from selected repo inputs (README, top-level structure, manifests, `docs/`). The normalized doc is the summary; `normalization_kind: curated_summary` flags it.
**Rationale.** A repo is heterogeneous; embedding "a concatenation of repo files" produces a generic centroid that drowns meaningful signal. Since git repos are cluster **seeds** ([D-8]), noisy seed embeddings degrade every downstream assignment. A curated summary fits the "one embedding per doc" invariant, makes the git adapter's job explicit, and aligns with how other sources work (Jira/RFP/transcripts are already curated representations of underlying activity).
**Alternatives.**
- Raw concatenation of repo content. Rejected: signal-degraded; bad seeds for clustering.
- Chunk + mean-pool only for git. Rejected: introduces asymmetric embedding logic; harder to reason about.
- Multi-vector per repo. Rejected: breaks the one-vector-per-doc invariant; would require generalizing clustering to multi-vector input. Possible v2 refinement.
**Trade-offs.** Adds an LLM call per repo at Ingest time (one-shot, cached). Quality of clustering now depends on the `summarize_repo` prompt and its eval set. Acceptable: repos are few (dozens at medium scale); the cost is small; the quality gain on seeds is large.

### [D-23] Raw evidence remains accessible to extractors
**Decision.** Extractors are not restricted to normalized docs. When `normalization_kind: curated_summary`, extractors MAY read the underlying `evidence/<source_type>/<source_id>/` for additional detail (e.g., requirement extraction from git reads the curated summary AND may consult specific code files referenced therein).
**Rationale.** Clustering needs a uniform, low-fidelity representation (the summary). Extraction needs high-fidelity, source-native evidence (the code). Forcing one shape on both wastes signal. Honest about the asymmetry: clustering reads summaries, extractors may dig deeper.
**Alternatives.**
- Only normalized docs are visible downstream. Rejected: requirements extraction from a 500-word repo summary loses too much; code-level requirements would be invisible.
- Mandate raw access for all extractors. Rejected: over-engineering for sources that are already curated (Jira tickets don't have a "deeper" form to consult).
**Trade-offs.** Extractors that consult `evidence/` are no longer purely source-agnostic — they need to know how to read git repo evidence specifically. Mitigation: the asymmetry is bounded to git in v1; if more source types grow `curated_summary` later, the pattern generalizes.

### [D-24] Local embedding model: nomic-embed-text-v1.5, pinned and vendored
**Decision.** Embeddings use `nomic-ai/nomic-embed-text-v1.5-GGUF` at a specific HuggingFace commit SHA, Q8_0 quantization, served via LM Studio's `/v1/embeddings` endpoint. The GGUF file is **vendored** into `models/embeddings/` for true reproducibility. The expected SHA-256 of the file is recorded in `config/clustering.yaml` and verified on load.
**Rationale.** Local-first removes a network dependency, removes per-call cost, and works offline. The GGUF path through LM Studio is more mature than MLX embedding ports in May 2026. Apache-2.0 license is clean for client work. 8k context handles long RFPs and transcripts without chunking. 768-dim vectors are cheap to store as sidecars. Vendoring the model means a `git clone` of the assessment is sufficient to reproduce.
**Alternatives.**
- OpenAI text-embedding-3-* (network dependency, per-call cost, vendor risk for client deliverables).
- MLX-native (Qwen3-Embedding-0.6B). Rejected as primary because LM Studio's MLX embedding path is less battle-tested; kept as a documented fallback in case the GGUF path has issues.
- Local without vendoring (rely on HF availability). Rejected: HF revisions can be force-pushed in rare cases; vendoring is the only true pin.
**Trade-offs.** Adds ~300MB to the repo (acceptable; the model is the heart of clustering reproducibility). Embedding quality is below frontier but plenty for cosine-similarity clustering at this scale. Quantization below Q8 is forbidden (Q4 degrades cosine quality meaningfully on embedding models, unlike LLMs).

### [D-25] Embeddings stored as sidecar files
**Decision.** Each `NormalizedDoc` has a co-located sidecar at `<source_id>.embedding.json` (§2.3 Embedding) containing the vector and its provenance (model, revision, prefix, content hash).
**Rationale.** Aligns with [D-1] filesystem-as-DB. Greppable, diffable, easy to inspect. Each sidecar is independently cacheable on its `content_hash` + model revision. Refreshing one embedding doesn't touch others.
**Alternatives.**
- Single `embeddings/` directory mirroring `normalized/`. Marginal benefit; loses co-location.
- Single binary index (Parquet, numpy memmap). Rejected: breaks filesystem-as-DB ethos; harder to inspect; better choice if scale grows beyond medium (then revisit, see [R-8]).
**Trade-offs.** Many small files. At medium scale (~few thousand docs × ~10KB sidecar each = ~tens of MB) this is fine. Beyond that, a binary index becomes attractive.

### [D-26] Single global similarity threshold, manually tuned
**Decision.** One `assignment_threshold` (default cosine 0.60) in `config/clustering.yaml` governs nearest-seed assignment for all source types. A `low_confidence_band` (default [0.55, 0.65]) flags borderline assignments for human review without rejecting them.
**Rationale.** Simplicity. Per-source thresholds add knobs without clear tuning signal at medium scale. The low-confidence band catches the cases where the threshold is wrong without forcing a re-run. Tuning is a small validation pass on a handful of representative docs.
**Alternatives.**
- Per-source-type thresholds. Rejected for v1: too many knobs without enough data to tune them. Open path if a specific source consistently misbehaves.
- Adaptive threshold per cluster density. Rejected: theoretically appealing but fiddly; the kind of thing that looks like a feature but is a leak.
- Top-k assignment (always assign to nearest seed, no threshold). Rejected: forces misfit assignments for docs that genuinely don't belong; loses the orphan-discovery path.
**Trade-offs.** A single threshold won't be optimal for every source type. Acceptable: the low-confidence band is the safety net, and misfilings can be hint-corrected via frontmatter (`assignment_hint`) when consistent.

### [D-27] HDBSCAN runs over unassigned docs only
**Decision.** HDBSCAN is not a primary clustering algorithm. It runs in phase 3a only over docs that were unassigned (below `assignment_threshold` against all seed clusters), to surface orphan clusters that don't correspond to any existing git repo.
**Rationale.** Repos are the strong prior ([D-8]); HDBSCAN is the fallback for genuine outliers (e.g., an RFP discussing a planned subsystem that doesn't yet have a repo). Running HDBSCAN over all docs would dilute the repo prior and produce unstable cluster identities across runs.
**Alternatives.**
- HDBSCAN over everything. Rejected: loses the repo prior; less stable.
- No HDBSCAN; unassigned docs stay unassigned. Rejected: legitimate orphan clusters (planned subsystems, cross-cutting concerns) would be lost.
**Trade-offs.** Two clustering mechanisms (nearest-seed + HDBSCAN). Acceptable: each is simple in isolation, and the boundary between them is the threshold, which is already a config knob.

### [D-28] Incremental re-clustering by default; full re-cluster on demand
**Decision.** Cluster assignments are stable across runs by default: new docs are assigned to existing clusters via the same nearest-seed + HDBSCAN logic, but existing assignments are not revisited. A `--full` flag forces a complete re-cluster from scratch. A `--full` is automatically triggered when `embedding.revision`, `similarity.assignment_threshold`, or HDBSCAN params change in `config/clustering.yaml`.
**Rationale.** Cluster identity stability matters during an iterative assessment — the consultant builds intuition about specific clusters, and shuffling identities mid-assessment is disorienting. New evidence usually fits existing clusters; the cost of incremental is low and the cost of unnecessary churn is high. When config changes invalidate the comparison basis, a full re-cluster is correct and automatic.
**Alternatives.**
- Always full re-cluster. Rejected: stable identities matter more than marginal accuracy gains on already-assigned docs.
- Pure incremental, no full mode. Rejected: incremental drift is real over many runs; full is the relief valve.
**Trade-offs.** Incremental can entrench bad assignments (a doc assigned wrong at iteration 3 stays wrong through iteration 20). Mitigation: low-confidence flags surface candidates for manual re-assignment; `cluster --full` is cheap because embeddings stay cached.

### [D-29] Eval scope is regression guard for LLM-driven steps; calibration is out of scope
**Decision.** Eval sets exist primarily as a **regression guard** for the five LLM-driven steps (`summarize_repo`, `discover_taxonomy`, `extract_requirements`, `extract_interactions`, `extract_domains`). They secondarily provide a **quality baseline** when first authored. They explicitly do **NOT** address calibration of consolidation scoring (confidence/criticality/review_priority) — that belongs to [OPEN-5].
**Rationale.** Three distinct purposes have three distinct shapes. Mixing them into one framework produces something that does none well. Regression guard wants reproducible pass/fail; calibration wants a continuous distribution of human judgments. Separating them keeps the eval framework simple and the calibration concern visible.
**Alternatives.**
- One framework covering all three. Rejected: scope creep; tooling becomes a kitchen sink.
- Skip eval sets entirely; rely on the consultant's vigilance. Rejected by [D-6]: silent regressions are the most likely failure of an LLM pipeline that iterates on prompts.
**Trade-offs.** Calibration is now a known gap with no infrastructure. Acceptable: it lives in [OPEN-5] and will get its own design when consolidation is deep-dived.

### [D-30] Per-style evaluation: full labels, assertions, LLM-as-judge, or hybrid — assigned per extractor
**Decision.** Each LLM-driven step uses an explicit evaluation style appropriate to its output shape, set in `config/eval.yaml`:

| Step                    | Style                         | Why |
|-------------------------|-------------------------------|-----|
| `summarize_repo`        | `llm_as_judge`                | Generative free-text; rubric scoring on template adherence and content coverage |
| `discover_taxonomy`     | `fully_labeled`               | Structured findings; exact comparison works |
| `extract_requirements`  | `llm_as_judge_plus_assertions`| Statements are hard to fully label; specific must-include cases are achievable |
| `extract_interactions`  | `fully_labeled`               | Highly structured output (kind, participants, endpoint) — exact comparison practical |
| `extract_domains`       | `assertions_only`             | Small enum + free name; assertions catch what matters; full labels are overkill |

**Rationale.** "Mix per extractor" is honest about the fact that no single eval style fits all output shapes. Free-form output needs rubric scoring; structured output enables exact-match scoring; small enums need only assertion checks. Assigning the style per step (and codifying it in `config/eval.yaml`) prevents drift and makes the trade-off explicit.
**Alternatives.**
- One style across all extractors. Rejected: forces poor fit somewhere.
- Free choice per case. Rejected: undermines comparability of runs over time.
**Trade-offs.** Five different ways to evaluate means five different mental models. Mitigation: each style has a single fixed schema in §2.3; the eval runner dispatches by `style` in config.

### [D-31] LLM-as-judge is pinned, cached, and judge-prompt-versioned
**Decision.** When a step uses LLM-as-judge, the judge model is pinned in `config/eval.yaml` (specific snapshot, `temperature=0`), the judge prompt is versioned in `config/prompts/judges/`, and judge calls go through the LLM cache like every other call. The cache key includes: `extractor_output + rubric + judge_prompt_version + judge_model`. The judge is typically a stronger model than the extractor itself (eval volume is low; cost is not the constraint).
**Rationale.** LLM-as-judge introduces a second source of non-determinism on top of the extractor being evaluated. Pinning everything makes the judgment reproducible; caching makes re-evaluation cheap; temperature=0 minimizes flakiness. Using a stronger judge model is affordable at eval volume and produces more reliable rubric scoring.
**Alternatives.**
- Run the judge N times and take majority. Rejected: redundant at temperature=0; expensive otherwise.
- Use the same model that produced the output as judge. Rejected: an extractor cannot fairly grade itself; well-documented bias.
- Skip caching for judge calls. Rejected: defeats reproducibility and re-evaluation cost.
**Trade-offs.** Judge model upgrades require a new pin and a fresh judge prompt evaluation. Mitigation: judge model pin is recorded in every `EvalRun`; comparisons across pins are explicit.

### [D-32] Eval is a separate command run before prompt changes ship; it does not block the pipeline
**Decision.** `python -m assessment eval <step>` (and `--all`) is a separate command the consultant runs manually after editing prompts or changing models. Eval results write to `config/evals/<step>/runs/<run_id>.json`. Pipeline stages (Extract, Cluster, Consolidate) do **not** check eval status and do not refuse to run on failing evals — the discipline is the consultant's responsibility, codified in the spec.
**Rationale.** Hard-gating bulk extraction on eval status adds machinery (file watchers, lockfiles) for marginal benefit at this scope. The consultant is the only operator; explicit discipline plus clear run records is sufficient. Pipeline runs that proceed despite known regressions leave an audit trail in `EvalRun` records and stage outputs, which is the right level of evidence.
**Alternatives.**
- Hard gate: extract refuses without a passing eval for the prompt version. Rejected: overhead for an internal tool; doesn't protect against the eval set being stale anyway.
- Auto-run eval on prompt-file save. Rejected: adds file watchers; surprises the consultant with API costs.
- Purely informational eval. Rejected by [D-6]: regressions slip in silently.
**Trade-offs.** A disciplined consultant who skips the eval step has no automated protection. Acceptable: this is an internal tool, not a regulated system. The spec records the expected workflow and the run records show whether it was followed.

### [D-33] Eval re-runs bypass the extractor cache; eval results have their own cache
**Decision.** When running `eval <step>`, the extractor call on each `EvalCase` bypasses the extractor's normal cache (a fresh call to the LLM is made, using the current prompt and model). The eval framework has its own cache, keyed on `(extractor_prompt_version, extractor_model, case_frozen_input_hash, judge_prompt_version, judge_model, rubric_hash)`. A second eval run with no changes is free; a change to any of those inputs invalidates the eval-cache entry.
**Rationale.** Cached extractor outputs from production runs may have been produced with old prompts. If the eval used those, it would be evaluating an old prompt, not the change being shipped. Bypassing the extractor cache forces eval to test the current state. The eval framework's own cache makes repeated identical runs free without conflating the two purposes.
**Alternatives.**
- Use the extractor cache. Rejected: silently evaluates stale outputs.
- No eval cache at all. Rejected: re-running eval after a one-line README edit shouldn't pay for fresh LLM calls.
**Trade-offs.** Two caches to reason about. Mitigation: both are content-addressed and committed to git; they don't interact except through being separate directories.

### [D-34] Two-stage requirement grouping: embedding pre-grouping + LLM verification
**Decision.** Consolidation groups requirements in two stages. First, embedding similarity above `grouping.embedding_threshold` produces candidate groups (deterministic, cheap, O(n²) similarity computation only within a cluster). Second, an LLM verification call per candidate group emits `confirm | split | reject`. Verification is cached on member content hashes + prompt version + model. An escape hatch (`grouping.llm_verification: false`) skips verification when cost-bounded.
**Rationale.** Pure embedding grouping misses paraphrased equivalents and over-groups near-but-different requirements. Pure LLM grouping is O(n²) per cluster and cost-prohibitive at medium scale. The two-stage approach uses embeddings to collapse the search space and the LLM to catch the cases embeddings miss. The escape hatch acknowledges that for rough first runs, embedding-only grouping is adequate signal.
**Alternatives.**
- Pure embedding similarity. Rejected: known failure modes on paraphrase and scope.
- Pure LLM grouping. Rejected: cost-prohibitive at medium scale.
- Three-stage with a re-verification pass. Rejected: marginal benefit for the cost.
**Trade-offs.** Two-stage means two failure surfaces (pre-grouping threshold + LLM verdict). Mitigation: pre-grouping threshold defaults are conservative (0.78); verification verdict and rationale are recorded in `groups.json` for inspection.

### [D-35] Conflict has explicit kinds with mixed deterministic and LLM detection
**Decision.** `Conflict.kind` is an enum (`contradiction | scope_mismatch | status_disagreement | version_skew | type_disagreement`). Status/type disagreements are detected deterministically from structured fields; version skew is detected deterministically (date spread) and confirmed by LLM; contradiction and scope mismatch are detected by LLM only. A single group can have multiple conflicts of different kinds.
**Rationale.** "Is there a conflict?" is a worse question than "what kind of conflict, and what's the evidence?" Different kinds need different detection (cheap structured checks vs. expensive LLM reasoning) and different review treatment (status disagreement is often informational; contradiction is always serious). Explicit kinds also make the review queue filterable and the calibration set easier to author.
**Alternatives.**
- Single boolean `conflict.present`. Rejected: loses signal; original v0 draft.
- Free-text conflict descriptions only. Rejected: not filterable; not aggregatable.
- LLM-only detection for all kinds. Rejected: wastes tokens on disagreements that are obvious from structured fields.
**Trade-offs.** Five kinds is a small taxonomy that may need extension (e.g., `priority_disagreement`). Acceptable: extending the kind enum is a config-level change; the framework absorbs new kinds without restructuring.

### [D-36] Confidence is a deterministic function of observable signals; LLM only writes the qualitative parts
**Decision.** `Confidence.score` is computed by a deterministic weighted formula over five signals (source count, authority-weighted agreement, recency spread, statement similarity, conflict presence). The LLM is **not** consulted for the score itself. The LLM IS consulted for the human-readable parts: `Conflict.description` and `Conflict.resolution.rationale`. Both signals and weights are recorded in the `Confidence` object for auditability.
**Rationale.** Confidence needs to be explainable to the client and tunable via calibration. A hybrid deterministic-plus-LLM-adjustment design is appealing on paper but in practice combines the worst of both: less reproducible than pure deterministic, less nuanced than pure LLM, and twice as hard to calibrate. Keeping the score deterministic and letting the LLM contribute to free-text fields preserves both auditability and prose quality. Calibration ([D-39]) tunes the weights, not individual scores.
**Alternatives.**
- Hybrid: deterministic base + per-item LLM adjustment. Rejected: explainability and calibration suffer; cost increases.
- Pure LLM-emitted confidence. Rejected: non-deterministic, hard to calibrate, hard to defend.
- Drop confidence as a score; surface raw signals. Rejected: loses the review-queue ordering signal.
**Trade-offs.** The deterministic formula will not capture every nuance. Mitigation: the five signals are a deliberately broad set covering source agreement, source authority, recency, and structural conflict — the dimensions that matter for an assessment. Edge cases that need finer reasoning surface through `Conflict.description`.

### [D-37] Criticality is LLM-emitted on a fixed discrete scale, with cluster summary as context
**Decision.** Criticality is one of four levels: `critical | important | moderate | minor`. The LLM emits the discrete level (not a float) via a single call with the resolved statement and the cluster's `summary.md` as context. The numeric value used for `review_priority` computation is looked up from `config/consolidation.yaml: criticality.numeric`. Cached on `hash(statement + cluster_summary_hash + prompt_version + model)`. The `change_plan_flag` is a separate, deterministic flag (true if any contributing requirement had `type: change_plan` or `status: planned | proposed`); it informs review-queue tags and an optional `change_plan_boost` to `review_priority`, but does not override criticality.
**Rationale.** "Is this requirement central or peripheral to the cluster's scope?" is genuinely fuzzy; LLM judgment with cluster context is the right tool. But emitting floats is spurious precision — LLMs are unreliable at fine-grained numeric scoring and the difference between 0.62 and 0.68 carries no real meaning. A four-level discrete scale is what an LLM can do reliably and what a reviewer can use. The numeric mapping is a config concern, not a model concern. Change plan items are explicitly tagged (so the consultant can filter to them) but not auto-promoted to "critical" — a minor change plan item is still minor.
**Alternatives.**
- Continuous 0..1 emitted by the LLM. Rejected: spurious precision; harder to calibrate.
- Five levels with explicit anchors. Rejected: four with named levels reads cleaner; the additional level adds ambiguity, not signal.
- Heuristic criticality from source authority and reference count. Rejected: a popularity proxy isn't importance.
- Constant criticality (drive priority from confidence only). Rejected: surfaces low-confidence trivia at the top of the queue.
**Trade-offs.** Discrete levels can cluster at coarse granularity (many "important"). The calibration loop ([D-39]) catches this if it actually matters for the consultant's prioritization.

### [D-38] Layered consolidation caching by content addressing
**Decision.** Consolidation cache operates at three levels: grouping (keyed on member content hashes + grouping config), conflict detection (keyed on group inputs), and criticality (keyed on statement + cluster summary hash). Each level invalidates independently. Changes to `config/consolidation.yaml` invalidate only the levels affected by the changed sections (e.g., changing source authorities affects grouping authority signals and reconciliation but not criticality).
**Rationale.** Consolidation is the most expensive stage (expensive reasoning model per [D-13]). Coarse caching would force full re-consolidation on small config edits; no caching would make iteration cost-prohibitive. Layered caching makes the cost of a change proportional to its scope.
**Alternatives.**
- Single cache key over all consolidation inputs. Rejected: any config edit triggers full re-consolidation.
- No cache. Rejected: cost-prohibitive.
**Trade-offs.** Cache invalidation logic is the most complex in the spec. Mitigation: each cache level is content-addressed and independently testable; the cache key derivation is a small pure function per level.

### [D-39] Calibration loop with human-gated weight tuning
**Decision.** Confidence weights and criticality assessment are calibrated against a hand-authored set of `CalibrationCase` records under `config/calibration/cases/`. Each case carries a frozen consolidated requirement, a hand-assigned target priority/criticality, and a rubric. The `calibrate:run` command runs the cases through current weights, judges them with the LLM-as-judge framework ([D-31]), and produces a `CalibrationRun` record. When tuning is warranted, the command proposes adjusted weights in `config/calibration/tuned_weights.yaml`; the consultant explicitly accepts via `calibrate:accept` (mirroring taxonomy lock per [D-20]). Tuned weights override defaults from `config/consolidation.yaml` when present.
**Rationale.** Scoring will be miscalibrated initially; that's [R-5]. Calibration is the structured response. Reusing the eval framework's LLM-as-judge ([D-31]) keeps the spec coherent. Human-gated acceptance prevents auto-tuned weights from drifting silently — the consultant is the source of truth for "what should be prioritized." Calibration is a regular activity (after first run, after model changes, when the consultant notices systematic miscalibration), not a one-shot.
**Alternatives.**
- Auto-accept tuned weights. Rejected: scoring drift becomes invisible; [D-20] parallel.
- No calibration; document scores as approximate. Rejected: punts on the [R-5] miscalibration risk; review-queue ordering becomes a guess.
- Continuous calibration via consultant feedback on every reviewed item. Rejected: too heavy a process for an internal tool; mismatch with the assessment's one-shot nature.
**Trade-offs.** Calibration requires the consultant to author ~50 cases and run the loop. This is real effort. Acceptable: it's the difference between a review queue the consultant can trust and one they have to re-rank by hand.

### [D-40] Cross-cluster reconciliation is its own stage with a priority boost
**Decision.** Cross-cluster reconciliation runs as Stage 4.5, separate from per-cluster consolidation. It takes all `ConsolidatedRequirement` records from non-archived clusters as input, produces `cross_cluster/conflicts.json` plus sidecar `cross_cluster_annotations.json` per affected cluster, and regenerates `review_queue.json` with a `cross_cluster_boost` (default 0.20) added to participating items' `review_priority`.
**Rationale.** The problem [OPEN-3] articulated is conflicts between sibling clusters that are missed by bottom-up consolidation; a separate stage is the cleanest place to put logic that requires global-scope inputs. The priority boost is the mechanism by which cross-cluster findings reach the consultant: without it, they sit in a separate artifact and may be overlooked. Reusing the embedding-then-LLM pattern from grouping ([D-34]) keeps the design coherent.
**Alternatives.**
- Inline in Stage 4 as a recursive root pass. Rejected: couples within-cluster and cross-cluster logic; cache invalidation becomes harder.
- A separate command rather than always running as part of `consolidate`. Rejected by [D-43] reasoning: silent skipping is worse than always running with the option to disable via config.
- No priority boost; just publish findings in a separate artifact. Rejected: cross-cluster findings have higher review value than within-cluster ones (per [OPEN-3] framing) and should be prioritized accordingly. Boost magnitude is calibratable.
**Trade-offs.** Extra phase to maintain; additional cost (one LLM call per surviving candidate after embedding filter). Acceptable: cost is bounded by `max_candidate_pairs`; cache reuse on stable inputs makes re-runs cheap.

### [D-41] Cross-cluster scope: contradiction and scope_mismatch only
**Decision.** Stage 4.5 detects only two of the five conflict kinds defined in [D-35]: `contradiction` and `scope_mismatch`. `status_disagreement`, `type_disagreement`, and `version_skew` are explicitly excluded.
**Rationale.** Same-named concepts in different clusters legitimately differ on status and type. A "user" requirement in the auth cluster and a "user" requirement in the analytics cluster aren't necessarily about the same user; their independent statuses are meaningful, not contradictory. Cross-cluster `version_skew` (same statement made twice in different subsystems at different times) is genuinely unusual and would mostly produce noise. The kinds that DO matter cross-cluster are real disagreements about what the system should do (contradiction) or for whom (scope_mismatch) — these are the kinds where being in different clusters is what makes them interesting.
**Alternatives.**
- All five kinds. Rejected: noisy; floods review queue with structural artifacts of clustering rather than real conflicts.
- Only contradiction. Rejected: scope_mismatch is exactly the kind of subtle cross-subsystem conflict the consultant most wants to know about.
**Trade-offs.** May miss legitimate cross-cluster status/type/version conflicts. Acceptable: these are rare enough that the consultant can surface them through ad-hoc review of the per-cluster outputs if needed.

### [D-42] Cross-cluster findings are sidecar annotations; per-cluster records remain immutable
**Decision.** Stage 4.5 does NOT modify `clusters/<cluster>/consolidated/requirements.json` (Stage 4's output). Instead, it writes `clusters/<cluster>/consolidated/cross_cluster_annotations.json` as a sidecar referencing the per-cluster `ConsolidatedRequirement` records that participate in cross-cluster conflicts. Downstream consumers (review queue, report) read both files together.
**Rationale.** Principle 2 (§1) — immutability of upstream layer outputs — is a core invariant of the design. Allowing Stage 4.5 to mutate Stage 4 outputs would break that invariant for a relatively narrow gain. Sidecar annotations preserve immutability, keep the bidirectional reference intact (annotation→conflict and conflict→annotation), and make re-runs of Stage 4.5 idempotent (overwrite the sidecar without touching the consolidated record).
**Alternatives.**
- Mutate per-cluster `requirements.json` directly. Rejected: breaks immutability principle.
- Push references only in one direction (conflict→record). Rejected: makes "what conflicts does this requirement participate in?" a search rather than a lookup; expensive for the report stage.
**Trade-offs.** Two files instead of one. Mitigation: review queue generation merges them; consultants who inspect raw files learn the convention quickly.

### [D-43] Cross-cluster reconciliation always runs by default; config-gated for cost
**Decision.** Stage 4.5 runs as part of every `consolidate` command by default. It can be disabled via `config/consolidation.yaml: cross_cluster.enabled: false` (config-level) or `--no-cross-cluster` (per-invocation). Disabling preserves Stage 4 outputs untouched; no annotations are written; review_queue.json is regenerated without cross-cluster contributions.
**Rationale.** Cross-cluster findings are the kind of thing easy to forget to run, and forgetting silently produces an inferior review queue. Making it the default protects against that. The config and CLI gates exist for cost-bounded runs (e.g., during prompt iteration on per-cluster consolidation) where cross-cluster cost is wasted.
**Alternatives.**
- Always opt-in. Rejected: easy to skip; spec wants the discipline by default.
- Always runs with no opt-out. Rejected: legitimate iteration scenarios shouldn't pay the full cost every time.
**Trade-offs.** Default cost is higher than per-cluster-only consolidation. Acceptable: cached candidates and verifications make re-runs cheap once the first run is done.

### [D-44] Hard candidate cap with halt-and-warn
**Decision.** Stage 4.5's pre-filtering enforces `cross_cluster.max_candidate_pairs` (default 500). If exceeded, the stage halts with a warning rather than proceeding silently. The consultant decides whether to raise the threshold (reducing candidate count) or raise the cap (accepting the cost).
**Rationale.** A corpus that produces 10,000 candidate pairs is signaling something — either the embedding threshold is too low, or the corpus has many similar-but-distinct requirements that legitimately exist (per-service variants of a pattern). Both situations warrant consultant judgment. Halting is louder than silent expensive runs.
**Alternatives.**
- No cap. Rejected: pathological corpora produce runaway cost.
- Soft cap with sampling. Rejected: introduces randomness; hard to reproduce results.
- Auto-raise threshold until under cap. Rejected: hides the signal that something is off.
**Trade-offs.** A first-run halt is disruptive. Acceptable: the warning is informative; the fix (raising threshold) is a one-line config change followed by a re-run, which is cheap because cached embeddings persist.

### [D-45] Report is a deterministic rendering of existing artifacts; no LLM calls
**Decision.** Stage 5.5 makes zero LLM calls. The report is purely a rendering of artifacts produced by upstream stages. All content — top-N items, landscape, freshness warnings, provenance — is computed from existing files using deterministic logic.
**Rationale.** The report's job is to *present* what the pipeline already produced, not to generate new analysis. Every interesting judgment (criticality, conflict rationale, cluster summaries) already has an LLM call and provenance elsewhere; replicating that work at report time would duplicate cost and introduce non-determinism. Deterministic rendering means the same inputs always produce the same report, which is essential for "what was true when this report was generated?" questions.
**Alternatives.**
- LLM-generated executive summary at report time. Rejected: duplicates work that consolidation already did; introduces non-determinism in the report's headline content.
- Re-run criticality/confidence at report time. Rejected: those belong to consolidation; re-running them mid-report would mean the report disagrees with `review_queue.json`.
- A "narrative" section that uses an LLM to synthesize themes. Rejected for v1: nice-to-have; can be added later as an optional section without changing the core. (Out of scope; see [R-25].)
**Trade-offs.** The report won't have the polished narrative an LLM could synthesize. Acceptable: the audience is the consultant, who is in the best position to synthesize from a structured first-read document.

### [D-46] Reports are always timestamped and never overwritten
**Decision.** Each `report` invocation writes a new file `reports/<ISO_timestamp>.md` (UTC, filename-safe form). Existing reports are never overwritten. There is no canonical "current" `report.md`.
**Rationale.** The consultant explicitly chose timestamped reports over git-history-based versioning. Honoring that means every report is a durable snapshot. Reports referencing specific pipeline state at the moment of generation should not be edited or replaced — they're an audit trail of "what we thought at this point."
**Alternatives.**
- Single `report.md` overwritten in place, git tracks history. Rejected by the consultant in favor of explicit snapshots. (Was the recommendation; not adopted.)
- Hybrid: `report.md` current plus `reports/<timestamp>.md` on demand. Rejected: complicates the mental model; the consultant gets the same effect via gitignore discipline (see [R-24]).
**Trade-offs.** Disk accumulation over many iterations. Mitigation: gitignore by default; commit only meaningful snapshots; see [R-24].

### [D-47] Freshness signals are first-class report content, not afterthoughts
**Decision.** The Health section of every report computes and surfaces concrete freshness signals: eval freshness per LLM-driven step, calibration staleness vs. consolidation config changes, taxonomy `--from-starting` shortcut detection, and best-effort model pin drift. Warnings appear both in the frontmatter (`freshness_warnings`) and in human-readable form in the Health section.
**Rationale.** [R-14] flagged that eval discipline is voluntary; the report is the natural place to surface "you skipped eval for this prompt change" warnings. Similar reasoning applies to calibration staleness and taxonomy shortcuts. Making these warnings unmissable (frontmatter + body) closes the gap between "the spec says do this" and "the spec helps you notice when you didn't."
**Alternatives.**
- Health as a separate command (`status` or `doctor`). Rejected: easy to skip; the report is where the consultant actually reads.
- Freshness as warnings in stage output only. Rejected: warnings during pipeline runs scroll past; report warnings persist as artifacts.
- No freshness signals; trust the consultant's discipline. Rejected: too much hard-won discipline elsewhere in the spec to abandon it here.
**Trade-offs.** Freshness checks add computation at report time and may produce false positives. Acceptable: computation is local (no LLM calls); false positives are informative not blocking.

### [D-48] Sections are independently authored and toggleable via config
**Decision.** The four sections (top_queue, landscape, health, provenance) are independent renderers. Each reads its own inputs and produces its own markdown block. The `sections` list in `config/report.yaml` controls which sections run and in what order; the default includes all four.
**Rationale.** Independence makes the rendering logic small and testable per section, lets the consultant disable sections they don't want (e.g., skip landscape for runs where they've memorized it), and makes future section additions (e.g., a narrative section per [R-25]) straightforward.
**Alternatives.**
- Monolithic renderer with the whole report in one function. Rejected: harder to maintain; loses per-section configurability.
- Fixed section order and presence. Rejected: less flexible; over-prescriptive for an internal tool.
**Trade-offs.** Per-section state (like the report frontmatter's `counts`) must be assembled before sections run, since multiple sections may use the same data. Acceptable: frontmatter assembly is its own 5.5a phase that runs first.

### [D-49] Archival is a flag, not a directory move
**Decision.** A cluster is archived by setting `archived: true` on its entry in `clusters/_index.yaml`. Cluster files (`summary.md`, `members.yaml`, `consolidated/*.json`, `cross_cluster_annotations.json`) stay in their current location at `clusters/<name>/`. The archival event captures `archived_at` (ISO timestamp) and `archived_at_versions` (snapshot of `consolidation`, `clustering`, and `taxonomy` config versions at archive time) so the consultant can later answer "what was the pipeline state when this cluster was archived?" without git archaeology.
**Rationale.** Filesystem moves are tempting for visual separation but break the stability of paths recorded in provenance records (every `ConsolidatedRequirement.cluster_path` would become stale). A flag preserves all existing references. The captured versions are honest about the snapshot nature of archived outputs without forcing freshness recomputation on every report.
**Alternatives.**
- Move to `clusters/_archived/<name>/`. Rejected: breaks provenance paths; complicates re-activation.
- Soft-delete (hide from default tooling, accessible via flag). Rejected: extra machinery for an internal tool; the flag is the soft-delete.
**Trade-offs.** Active and archived clusters mix in the directory listing. Acceptable: `_index.yaml` is the canonical source of truth; `find clusters/ -maxdepth 1 -type d` is a stale way to enumerate; tooling should read `_index.yaml`.

### [D-50] Archival is manual; no automation triggers it
**Decision.** Archival happens only when the consultant explicitly edits `_index.yaml`. No automation (e.g., archiving when a git repo is removed from the source system) applies. Unarchival is the symmetric manual operation.
**Rationale.** Aligns with the spec's pattern of "consultant's discipline, codified" (eval discipline per [D-32], calibration acceptance per [D-39], taxonomy lock per [D-20]). Auto-archival on source-system changes introduces a class of surprises ("my repo was archived because someone toggled a flag upstream") that the consultant would have to reason about. Manual is reversible by trivial edit; automatic decisions need to be discovered and undone.
**Alternatives.**
- Auto-archive when a git repo is removed/archived in the source system. Rejected: couples spec to source-system semantics; reversibility is awkward.
- Manual + automatic suggestion (warn but don't auto-apply). Rejected for v1; future enhancement if assessments grow long-running enough to make manual oversight expensive.
**Trade-offs.** A consultant working with many sources may forget to archive obviously-defunct clusters. Acceptable: the cost is keeping a few stale clusters in active processing, not a correctness failure; the report's landscape section makes them visible.

### [D-51] Each stage that processes clusters checks the archived flag independently
**Decision.** Stages 3b (semantic labeling), 3c (hierarchy), 4 (consolidation), 4.5 (cross-cluster reconciliation), and 5.5 (report landscape) each independently read the `archived` flag and apply it. Archived clusters are excluded from:
- Stage 3b: summary regeneration. The existing `summary.md` stays as-is.
- Stage 3c: super-cluster proposal candidates.
- Stage 4: consolidation gathering (parents skip archived child outputs entirely).
- Stage 4.5: the global pool for embedding pre-filtering and verification.
- Stage 5.5 (landscape): full rendering. Archived clusters get a de-emphasized minimal entry instead.

**Rationale.** Each stage knows what "archived means" in its own terms (skip vs. de-emphasize vs. exclude-from-pool). A centralized `active_clusters()` helper would either return the same list in all five cases (and miss the report's different rendering) or be parameterized in ways that obscure each stage's actual behavior. Independent checks keep each stage's archival semantics inline with the stage that implements them.
**Alternatives.**
- Centralized `active_clusters()` helper. Rejected: hides per-stage variation; e.g., the report needs to see archived clusters for de-emphasized rendering, which the helper would have to expose anyway.
- File-level marker (e.g., `clusters/<name>/.archived` file) that excludes via glob. Rejected: side-effect-based; bad fit for filesystem-as-DB (Principle 1); harder to reason about.
**Trade-offs.** Duplication of the "filter out archived" pattern across five stages. Mitigation: the pattern is one line each; the alternative is hiding semantics behind an abstraction that varies per caller anyway.

### [D-52] Member docs of archived clusters stay put
**Decision.** When a cluster is archived, its members listed in `clusters/<name>/members.yaml` remain members of that cluster. They are NOT released to the unassigned pool. They are NOT re-eligible for assignment to other active clusters via incremental re-clustering. Each normalized doc has exactly one cluster assignment, which is preserved across archival.
**Rationale.** The simplest possible semantics. "Archived" means the cluster (and everything in it) is no longer in active processing scope. If the consultant wants those docs in an active cluster, they unarchive (cluster comes back with members intact) or do a full re-cluster (`cluster --full`), which discards `_assignments.json` and re-assigns from scratch.
**Alternatives.**
- Release members to unassigned pool. Rejected: causes member churn on archive/unarchive cycles; surprises the consultant; can change other clusters' membership.
- Members stay in archived cluster AND become eligible for re-clustering (dual membership). Rejected: complicates the schema (multi-cluster membership); semantically muddied.
**Trade-offs.** A doc that legitimately belongs in an active cluster but happens to be in an archived one stays "stuck" until the consultant intervenes (unarchive, or full re-cluster). Acceptable: the consultant who archives a cluster is taking responsibility for it; tooling can surface this via the report (count of "docs in archived clusters" is visible in the Provenance section).

---

## 5. Known Risks

Risks we've accepted, with mitigations.

### [R-1] Agent-based orchestration appeals; deterministic orchestration was chosen
The user initially leaned toward agent-based execution. We pushed back: agent orchestration stacks non-determinism, makes debugging hard, burns tokens reasoning about work rather than doing it, and undermines reproducibility — exactly where we need it. Decision is [D-14]. If a user-facing chat interface over the assessment results is desired later, it's a separate layer that reads the artifacts the deterministic pipeline produces.

### [R-2] Cross-cluster reconciliation is targeted, not exhaustive
Stage 4.5 ([D-40]) addresses the most valuable form of cross-cluster conflict (sibling-subtree contradictions and scope mismatches between similar-statement requirements) but does not exhaustively compare every pair of requirements across the entire tree. By design ([D-41], [D-44]), it skips `status_disagreement` and `type_disagreement` (legitimate cross-cluster differences) and bounds the candidate pool by embedding similarity. Conflicts that don't surface via embedding similarity (e.g., very different vocabulary describing the same conflict) will not be detected. Acceptable: the trade-off is between cost-bounded findings the consultant can act on and an unbounded "find every possible conflict" that produces too much noise to use.

### [R-3] Embedding-based cluster assignment will misfile some docs
A Jira ticket can semantically match repo A but actually be about repo B. Mitigations:
- Use explicit hints in normalized frontmatter where available (e.g., Jira `component` → repo mapping).
- Surface low-confidence assignments in a review queue, not silently.
- Accept that 5–10% misfiling is fine at the assessment stage.

### [R-4] Prompt drift invalidates cache
Tuning prompts during the assessment invalidates cached outputs for that extractor. Cache key includes prompt version (so this is *correct*, not buggy), but it means budget for regeneration on prompt changes. Mitigation: stabilize prompts on a small sample before running across all evidence.

### [R-5] Confidence and criticality scoring is uncalibrated initially
First runs will produce a noisy review queue. The calibration loop ([D-39]) is the structured response: hand-author ~50 `CalibrationCase` records, run `calibrate:run`, review proposed weights, accept via `calibrate:accept`. See also [R-20] (calibration requires consultant labor).

### [R-6] Source-authority weights are configured guesses
`config/consolidation.yaml: source_authority` ships with default weights (RFP 1.0, code 0.8, Jira 0.6, etc.) that are reasonable but not validated for any specific client. The defaults affect reconciliation outcomes and the authority-weighted-agreement signal in confidence. Mitigation: the calibration loop ([D-39]) catches systematic mismatch with the consultant's prioritization; authority weights are config, not code; the consultant can tune them mid-assessment with selective cache invalidation per [D-38]. RFP isn't always more authoritative than Jira — recency vs authority trade-offs are encoded in the deterministic ordering of reconciliation rules and the relative weights, both of which are tunable.

### [R-7] Lossy normalization for complex sources
Spreadsheets with rich formatting, RFPs with embedded tables/images, and transcripts with speaker overlap may lose information at normalization. Mitigation: preserve original in `evidence/`; surface "normalization warnings" alongside the normalized doc.

### [R-8] Filesystem scaling
At medium scale (dozens of repos, thousands of tickets), the filesystem is fine. If scope grows to large (hundreds of repos, 10k+ tickets), expect: slow `git status`, slow recursive listings, and pressure to introduce an index. Mitigation: revisit at that point, not pre-emptively.

### [R-9] Taxonomy discovery suffers from sample-driven blindness
Stage 1.5 samples ~15 docs per source type. A source type with subtle distinctions that only appear in unsampled docs will leave gaps in the locked taxonomy. Mitigations: the starting taxonomy is a floor ([D-18]) so legitimate values aren't silently pruned; the discovery proposal flags low-confidence single-finding additions for explicit consultant review; [D-21] explicitly allows documenting post-lock gaps without restarting.

### [R-10] Discovery and extraction cost coupling
Re-running Stage 1.5 produces a new `taxonomy.locked.yaml` version, which invalidates the entire extraction cache via the cache key (§3, Stage 2). This is correct behavior but it means a small late-stage taxonomy edit costs a full re-extraction. Mitigation: lock once, lock well, and use [D-21] to defer non-critical taxonomy revisions to a future run rather than mid-assessment.

### [R-11] Repo summary is a single LLM call that drives cluster seeding
Cluster seeds come from git-repo curated summaries ([D-22]). A weak or misleading summary contaminates every downstream assignment to that cluster. Mitigations: eval set for `summarize_repo` includes repos with non-obvious structure; the consultant can manually edit `normalized/git/<repo>.md` after Ingest (the next `embed` run refreshes the sidecar and the next `cluster` run reflects the edit); the `Notes` section explicitly invites uncertainty flagging.

### [R-12] Local embedding model quality is below frontier
`nomic-embed-text-v1.5` is good enough for cosine-similarity clustering of moderately-sized docs but is not state-of-the-art. Edge cases (technical jargon-heavy transcripts, multilingual content, deeply contextual short documents) may cluster poorly. Mitigations: low-confidence band surfaces borderline assignments for review; `assignment_hint` frontmatter overrides; the fallback path to a stronger model (Qwen3-Embedding-0.6B or a network model) is documented if a specific corpus genuinely defeats the local model.

### [R-13] Repo summary LLM may miss non-obvious code patterns
The summarize_repo prompt sees README, top-level structure, manifests, and `docs/`. Code in less-discoverable locations (deep packages, dynamically loaded modules) won't appear in the summary unless the README or docs mention it. Acceptable for clustering (which is about coarse organization), but it means the repo summary should never be treated as a substitute for the actual code during extraction ([D-23] addresses this by allowing extractors to read raw evidence).

### [R-14] Eval discipline is a human practice, not enforced
[D-32] makes eval explicit but optional from the pipeline's perspective. A consultant who skips eval after changing a prompt has no automated guardrail. Mitigation: every `EvalRun` records the prompt and model versions; the absence of a recent passing run for the current prompt version is detectable; the report stage (§3 Stage 5, future work via [OPEN-6]) can surface "no recent passing eval for prompt vX" as a warning.

### [R-15] LLM-as-judge has systematic biases
The judge model is itself a stochastic process. Known biases include preference for verbose responses, agreement with the extractor's framing, and inconsistency on borderline cases. Mitigations: judge prompt is reviewed and versioned ([D-31]); temperature=0 minimizes flakiness; a stronger model than the extractor reduces certain biases; the borderline band surfaces cases the judge isn't confident about for human review. Residual bias remains a known limitation.

### [R-16] Eval sets can be gamed by overfitting prompts to them
Iterating prompts until "all evals pass" risks overfitting: the prompt learns to satisfy specific eval cases without generalizing. Mitigations: eval cases are seeded from diverse taxonomy discovery samples ([D-29]); cases added later come from real regressions (independent of prompt design); per-case borderline flags catch local optima.

### [R-17] Eval-set staleness
Eval sets capture a snapshot of representative cases. As the corpus changes (new source types, new content categories), eval coverage degrades. Mitigation: when taxonomy discovery is re-run (new evidence added), `eval:seed` can produce new candidate cases from the latest discovery samples; the consultant decides whether to label and adopt them.

### [R-18] Grouping is the longest-lever single failure in consolidation
A bad grouping decision (over-merge or under-merge) propagates through everything downstream: conflict detection sees the wrong members, reconciliation produces a wrong resolved statement, scoring is computed against the wrong set. Mitigation: groups are persisted as their own artifact (`groups.json`) for inspection; LLM verification verdicts are recorded with rationale; manual override of grouping is supported by editing `groups.json` and re-running consolidation (cache picks up the new grouping automatically).

### [R-19] Calibration requires consultant labor
[D-39] mandates hand-authored calibration cases. ~50 cases at ~5–10 minutes each is several hours of focused work. A consultant who skips this step is left with default weights and uncalibrated criticality. Mitigation: the spec explicitly documents this as the cost of trustworthy scoring; the calibration case authoring can be staged (start with 10–15 cases for first calibration, grow over time); the calibration set is reusable across assessments for the same client.

### [R-20] Manual reconciliation overrides go stale silently
A `config/consolidation_overrides/<group_id>.yaml` authored when a group had three members becomes orphaned when extraction changes the group's membership and thus its `group_id`. Mitigation: stale overrides emit warnings at consolidation time (their `group_id` is no longer present in `groups.json`); the consultant decides whether to update or delete.

### [R-21] Cross-cluster candidate explosion on clustered corpora
Some corpora (e.g., microservice ecosystems with shared patterns repeated per service) produce many cross-cluster candidate pairs because the same statements legitimately recur. The hard cap ([D-44]) prevents runaway cost but doesn't solve the underlying signal-to-noise problem. Mitigation: raise the embedding threshold; the consultant accepts that very-similar-but-legitimately-distinct requirements aren't real conflicts.

### [R-22] Cross-cluster LLM verification false negatives are invisible
When the verifier rejects a candidate as `not_a_conflict`, that decision is cached and not revisited unless cache keys change. A genuine but subtle conflict that the LLM missed on first pass will stay missed. Mitigation: the `needs_review` verdict catches the uncertainty cases; the consultant can review `cross_cluster/conflicts.json` for `not_a_conflict` entries when investigating specific concerns; future verifier prompt improvements invalidate the cache and re-verify.

### [R-23] Cross-cluster boost may distort priority for low-criticality items
A `minor`-criticality cross-cluster conflict gets `0.15 * 0 + 0.20 = 0.20` priority, which could float above a `moderate`-criticality non-conflict item at `0.40 * 0.5 = 0.20`. Whether this is correct is calibration territory. Mitigation: the calibration loop ([D-39]) can include cross-cluster cases; the boost is tunable.

### [R-24] Reports/ accumulates without bound
Every `report` invocation writes a new timestamped file ([D-46]). Over many iterations of an assessment, `reports/` can accumulate dozens to hundreds of files. Mitigation: the recommended discipline is to gitignore `reports/*.md` except for snapshots the consultant explicitly wants to commit (e.g., before-and-after comparisons around major prompt or model changes). The spec does not enforce a retention policy; the consultant manages it. A future `report:prune --older-than <days>` command could automate this; out of scope for v1.

### [R-25] No narrative synthesis in the report
[D-45] keeps the report deterministic and rendering-only — no LLM-generated executive summary or theme synthesis. The consultant has to do the synthesis when they write the client deliverable. Acceptable: synthesis is the consultant's value-add; automating it would either be low-quality or non-reproducible. A future optional narrative section could be added without changing the core architecture, gated by an explicit `sections: [... , narrative]` opt-in.

### [R-26] Archived clusters' outputs reflect their archive-time configuration, not current
Archived clusters' `summary.md` and `consolidated/*.json` files are frozen at archive time ([D-49]). If `config/consolidation.yaml` or prompts change after archival, those outputs no longer reflect current logic. Mitigation: `archived_at_versions` captures the configs in effect at archive time, so the consultant can answer "is this output current?" by comparing versions. The report does NOT automatically warn about this — by [D-50] reasoning, archived means archived; the consultant knows it's a snapshot. If they want current outputs, unarchive.

### [R-27] Docs stuck in archived clusters
Per [D-52], member docs of an archived cluster stay there. A doc that legitimately belongs in an active cluster but happens to be in an archived one is "stuck" — it doesn't contribute to any active cluster's summary or consolidation. Mitigation: the Provenance section of the report counts "documents in archived clusters" so the consultant can see at a glance whether this matters; unarchival or `cluster --full` are the resolution paths.

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

### ~~[OPEN-2] Eval-set construction strategy~~ — RESOLVED
**Status.** Resolved with a full eval framework. Five eval sets in v1, per-style evaluation appropriate to each output shape, seeded from taxonomy discovery samples and grown incrementally with real regressions.

**Where the resolution lives:**
- Scope: regression guard + quality baseline; calibration explicitly out of scope. See [D-29].
- Coverage: 5 eval sets (`summarize_repo`, `discover_taxonomy`, `extract_requirements`, `extract_interactions`, `extract_domains`). Updated [D-6].
- Data shapes: `Eval configuration`, `EvalCase`, `JudgeVerdict`, `EvalRun` in §2.3.
- Directory layout: `config/eval.yaml`, `config/evals/<step>/{cases,runs}/`, `config/prompts/judges/` in §2.2.
- Per-style assignment: `summarize_repo` → llm_as_judge; `discover_taxonomy` → fully_labeled; `extract_requirements` → llm_as_judge_plus_assertions; `extract_interactions` → fully_labeled; `extract_domains` → assertions_only. See [D-30].
- Judge handling: pinned model, temperature=0, versioned judge prompts, cached. See [D-31].
- Pass/fail gate: per-step thresholds + borderline band + human review for borderline. Eval is a separate command run by the consultant; does not block the pipeline. See [D-32].
- Cache strategy: extractor cache bypassed during eval; eval has its own content-addressed cache. See [D-33].
- Seeding: `eval:seed` command produces unlabeled `EvalCase` stubs from taxonomy discovery samples ([R-17] addresses ongoing staleness).
- Risks: [R-14] eval discipline is voluntary; [R-15] judge bias; [R-16] overfitting risk; [R-17] eval staleness.

**Couples with:**
- [OPEN-5] consolidation calibration (out of scope here by [D-29]).
- [OPEN-6] reporting layer (could surface "no recent passing eval" warnings, per [R-14]).

### ~~[OPEN-3] Cross-cluster conflict reconciliation~~ — RESOLVED
**Status.** Resolved with Stage 4.5 (Cross-cluster Reconciliation): embedding pre-filtering with conservative threshold, LLM verification, sidecar annotations preserving immutability of per-cluster outputs, configurable priority boost for surfaced findings, hard candidate cap with halt-and-warn.

**Where the resolution lives:**

Pipeline (§3 Stage 4.5): four phases (embedding pre-filtering, LLM verification, emit annotations, regenerate review queue).

Data shapes (§2.3):
- `CrossClusterCandidate` — intermediate output of embedding pre-filtering.
- `CrossClusterConflict` — verified records with explicit verdicts (`confirmed_conflict | not_a_conflict | needs_review`).
- `CrossClusterAnnotation` — sidecar files referencing per-cluster records (immutability preserved).
- `ReviewQueueItem` expanded with `cross_cluster_conflicts` field, `cross_cluster_conflict` tag, and `review_priority_components` breakdown.
- `config/consolidation.yaml: cross_cluster` section — threshold, kinds, cap, boost, enable flag.

Directory layout (§2.2): `cross_cluster/` top-level directory; per-cluster `consolidated/cross_cluster_annotations.json` sidecar.

Decisions:
- [D-40] Stage 4.5 as separate phase with priority boost (resolves the framing pushback).
- [D-41] Conservative scope: `contradiction` and `scope_mismatch` only (resolves the noise concern).
- [D-42] Annotations as sidecar files (resolves immutability tension).
- [D-43] Always runs by default; config-gated for cost.
- [D-44] Hard candidate cap with halt-and-warn (resolves cost-runaway concern).

Orchestration (§3 Stage 5): `consolidate` always runs Stage 4.5; `--no-cross-cluster` flag for opt-out.

Risks: [R-2] updated to reflect targeted-not-exhaustive scope; new [R-21] (candidate explosion), [R-22] (verification false negatives), [R-23] (boost may distort low-criticality priority).

**Couples with:**
- [OPEN-5] consolidation infrastructure — Stage 4.5 reuses the embedding wrapper, the conflict-kind enum, and the calibration framework. The CalibrationCase schema already supports cross-cluster examples per [D-40] rationale.
- [OPEN-6] reporting layer — the review queue's `tags`, `cross_cluster_conflicts`, and `review_priority_components` are natural surfaces for the report.

### ~~[OPEN-4] Clustering algorithm specifics~~ — RESOLVED
**Status.** Resolved by pinning embedding model, defining the structural-phase algorithm in detail, and capturing the supporting decisions.

**Where the resolution lives:**
- Embedding model: pinned `nomic-ai/nomic-embed-text-v1.5-GGUF`, vendored locally; see [D-24] and `config/clustering.yaml` (§2.3).
- Embedding unit: one vector per `NormalizedDoc`, with git getting an LLM-curated summary first ([D-22]).
- Embedding storage: sidecar files ([D-25]).
- Prefix convention: `clustering: ` baked into the embedding wrapper (§2.3 Embedding).
- Algorithm: nearest-seed assignment with cosine threshold, fallback HDBSCAN over unassigned; full details in §3 Stage 3a.
- Threshold: single global cosine 0.60 with low-confidence band [0.55, 0.65]; tunable in config ([D-26]).
- HDBSCAN scope: unassigned docs only, fixed seed ([D-27]).
- Re-clustering: incremental by default with `cluster --full` escape hatch and automatic full re-cluster on config changes ([D-28]).
- Determinism: same embeddings + same config = same assignments; explicit tie-breaking on `source_id`.

**Still couples with [OPEN-2]** (eval-set construction): the `summarize_repo` prompt needs its own eval set, with examples that include repos with non-obvious structure ([R-11], [R-13]).

### ~~[OPEN-5] Consolidation schema for requirements~~ — RESOLVED
**Status.** Resolved with a full consolidation design: grouping, conflict detection (with explicit kinds), reconciliation rules, deterministic confidence, LLM-emitted criticality on a discrete scale, and a calibration loop. The calibration concern punted from [OPEN-2] via [D-29] is now addressed by [D-39].

**Where the resolution lives:**

Data shapes (§2.3):
- `Consolidation configuration` — all knobs in `config/consolidation.yaml`.
- `RequirementGroup` — persisted between phases for inspectability.
- `Conflict` — explicit `kind` enum with five values; structured evidence; resolution rationale.
- `Confidence` — score + signals + weights, fully auditable.
- `Criticality` — discrete level + numeric mapping + LLM rationale.
- `ConsolidatedRequirement` — single resolved `type` and `status`; disagreements surface via `conflicts[]`; `change_plan_flag` for filtering.
- `ReviewQueueItem` — adds `cluster_path` and derived `tags` for filtering.
- `CalibrationCase` — frozen consolidated requirement + target priority + rubric.
- `CalibrationRun` — run record + proposed tuned weights.

Pipeline (§3 Stage 4): six phases (gather, group, conflict-detect, reconcile, score, emit) with layered caching ([D-38]).

Decisions:
- [D-34] Two-stage grouping (embedding pre-grouping + LLM verification).
- [D-35] Multiple conflict kinds with mixed deterministic/LLM detection.
- [D-36] Deterministic confidence; LLM only for qualitative parts (resolves the hybrid-confidence pushback).
- [D-37] Discrete criticality scale; cluster summary as context; change_plan handled via tagging not auto-promotion.
- [D-38] Layered consolidation caching.
- [D-39] Calibration loop with human-gated weight tuning (resolves [D-29] punt).

Orchestration (§3 Stage 5): added `calibrate:run` and `calibrate:accept` subcommands.

Risks: [R-5] updated to point at the calibration mechanism; [R-6] expanded to reflect new config layout; new risks [R-18] (grouping is the longest lever), [R-19] (calibration labor), [R-20] (stale manual overrides).

**Couples with:**
- [OPEN-3] cross-cluster reconciliation — explicitly out of scope here; the consolidation schema supports it when [OPEN-3] is tackled (each `ConsolidatedRequirement` can be input to another consolidation pass at a higher level, including a global root pass).
- [OPEN-6] reporting layer — review queue tags and calibration freshness are natural surfaces for the report stage.

### ~~[OPEN-6] Reporting layer~~ — RESOLVED
**Status.** Resolved with Stage 5.5 (Report): timestamped, deterministically rendered markdown documents with four sections (top-N queue, landscape, health, provenance), self-describing frontmatter capturing every input version, and first-class freshness signals that close the loop on voluntary disciplines elsewhere in the pipeline.

**Where the resolution lives:**

Pipeline (§3 Stage 5.5): six phases (frontmatter assembly, top-N rendering, landscape, health/freshness, provenance, write).

Data shapes (§2.3):
- `Report configuration` — top-N size, freshness thresholds, section toggles, provenance options.
- `ReportRun` — YAML frontmatter capturing input versions, freshness warnings, and counts; written into every report.

Directory layout (§2.2): `reports/<ISO_timestamp>.md`; `config/report.yaml`.

Decisions:
- [D-45] Deterministic rendering; no LLM calls (resolves the pushback on the LLM-narrative temptation).
- [D-46] Always timestamped; never overwritten (consultant's explicit choice over git-history-based versioning).
- [D-47] Freshness signals are first-class — closes the loop on [R-14] (voluntary eval discipline), calibration staleness, and the [D-19] taxonomy shortcut.
- [D-48] Sections are independently authored and toggleable via config.

Orchestration (§3 Stage 5): `report` subcommand updated to reference Stage 5.5.

Risks: [R-24] `reports/` accumulates without bound; [R-25] no narrative synthesis (synthesis stays the consultant's job).

**Couples with:**
- [R-14] eval discipline is voluntary — freshness signals surface skipped evals.
- [D-19] taxonomy `--from-starting` shortcut — surfaced as a warning so consultants don't forget they used it.
- Future narrative section ([R-25]) — pluggable via [D-48] section list; out of scope for v1.

### ~~[OPEN-7] What to do with archived clusters' content~~ — RESOLVED
**Status.** Resolved with explicit archival semantics codified across the spec. The default proposal in this open question (excluded from summarization/consolidation/review queue, readable for context) is honored; the resolution adds precision about the flag mechanism, the captured archive-time versions, per-stage handling, and member-doc fate.

**Where the resolution lives:**

Data shapes (§2.3): `Cluster entry` extended with `archived_at` and `archived_at_versions` fields; archival semantics codified inline.

Pipeline:
- Stage 3b/3c (§3 Stage 3): non-archived only; archived clusters' summaries frozen.
- Stage 3d (§3 Stage 3): archival is a manual flag with captured archive-time versions.
- Stage 4 (§3 Stage 4a): non-archived only; archived child outputs not propagated.
- Stage 4.5 (§3 Stage 4.5a): archived clusters excluded from the global pool.
- Stage 5.5 (§3 Stage 5.5c, 5.5e): landscape de-emphasizes archived; provenance counts active vs archived plus docs-in-archived.

Decisions:
- [D-49] Archival is a flag, not a directory move. Cluster files stay; `archived_at_versions` captures snapshot context.
- [D-50] Archival is manual; no automation. Aligns with the "consultant's discipline" pattern.
- [D-51] Each stage checks the flag independently — keeps per-stage semantics inline.
- [D-52] Member docs stay put on archival; unarchival or `cluster --full` are the resolution paths.

Risks: [R-26] archived outputs are snapshots, not current (no auto-warning, by design); [R-27] docs stuck in archived clusters (visible in report Provenance section).

**Couples with:**
- [D-28] incremental re-clustering — `cluster --full` is the escape hatch for releasing members from archived clusters.
- [D-47] freshness signals — by [R-26], archive staleness is deliberately NOT in the freshness signal set; archived means archived.

### ~~[OPEN-8] Taxonomy validation on real evidence~~ — RESOLVED
**Status.** Resolved by introducing **Stage 1.5 · Taxonomy Discovery** as a blocking pre-Extract stage. The manual procedure originally proposed was upgraded to an automated, bounded discovery loop with human-reviewed lock.

**Where the resolution lives:**
- Stage definition: §3, Stage 1.5.
- Data shapes: §2.3, `Starting/Locked Taxonomy`, `TaxonomyFinding`, `Taxonomy Findings consolidated`.
- Directory layout: §2.2, `taxonomy/` and `config/taxonomy.{starting,locked}.yaml`.
- Decisions: [D-17] termination, [D-18] floor-not-reset, [D-19] blocking-prerequisite, [D-20] human-reviewed lock, [D-21] post-lock debt handling.
- Risks: [R-9] sample-driven blindness, [R-10] discovery vs. extraction cost tension.

**Still couples with [OPEN-2]** (eval-set construction): the docs sampled during discovery are good seeds for the per-extractor eval set, and the locked taxonomy is the schema those evals must satisfy.

---

## 7. Glossary

- **Evidence** — Raw, immutable, ingested artifact in its source-native form.
- **Normalized document** — Uniform `{markdown + frontmatter}` representation of an evidence item.
- **Normalization kind** — `raw_text` (direct rendering) or `curated_summary` (LLM-generated representation of larger evidence; currently only git). See [D-22].
- **Repo summary** — A fixed-template, LLM-generated curated summary of a git repo, serving as the normalized doc for `source_type: git`. See §2.3 RepoSummary and [D-22].
- **Starting taxonomy** — The initial enum values defined in §2.3, serving as the floor for discovery.
- **Locked taxonomy** — The reviewed, accepted taxonomy produced by Stage 1.5 and consumed by Stage 2. Lives in `config/taxonomy.locked.yaml`.
- **Taxonomy discovery** — Stage 1.5: a bounded discovery loop that samples normalized docs per source type, identifies taxonomy gaps and ambiguities, and proposes refinements for human review.
- **Advances learning** — A discovery iteration advances learning iff it introduces a new proposed enum value, a new ambiguity pair, or a new gap report. See [D-17].
- **Extraction** — Structured JSON derived from a normalized document (requirements, interactions, domains).
- **Embedding sidecar** — A JSON file co-located with each normalized doc, holding the vector and its provenance (model, revision, prefix). See §2.3 Embedding and [D-25].
- **Seed cluster** — A cluster created from a non-archived git repo; serves as a reference point for nearest-neighbor assignment of other docs. See [D-8].
- **Orphan cluster** — A cluster discovered by HDBSCAN among unassigned docs, with no corresponding git repo seed. See [D-27].
- **Low-confidence assignment** — An assignment whose similarity falls within `low_confidence_band` (default [0.55, 0.65]); recorded normally but flagged for human review. See [D-26].
- **Cluster** — A grouping of normalized documents with its own summary and consolidated outputs.
- **Super-cluster** — A parent cluster grouping sibling sub-clusters.
- **Consolidation** — The process of grouping extracted requirements within a cluster, resolving conflicts, and scoring for review.
- **Review queue** — A ranked list of consolidated requirements that need human attention, ordered by `review_priority`.
- **Provenance** — The chain of source artifacts, models, and prompt versions that produced a derived artifact.
- **Incremental re-clustering** — Default re-clustering mode: existing assignments preserved; only new or changed docs are assigned. See [D-28].
- **Full re-cluster** — `cluster --full`: discard all assignments, re-run phase 3a from scratch. Triggered automatically on certain config changes.
- **Eval set** — A versioned collection of `EvalCase` records under `config/evals/<step>/cases/` used to detect regressions in an LLM-driven step. See [D-6] and [D-29].
- **Evaluation style** — How an `EvalCase` is judged: `fully_labeled` (exact-match), `assertions_only` (must-include / must-not-include rules), `llm_as_judge` (rubric-scored), or `llm_as_judge_plus_assertions` (rubric plus rules). Assigned per step in `config/eval.yaml`. See [D-30].
- **Judge** — A pinned LLM that scores extractor output against a versioned rubric for `llm_as_judge` styles. Not the same model as the extractor. See [D-31].
- **EvalRun** — A record of one eval invocation: which prompt and model were tested, which cases ran, what verdict each case received, and the aggregate pass/fail. Lives at `config/evals/<step>/runs/<run_id>.json`. See §2.3.
- **Borderline case** — An eval case whose score falls inside the configured `borderline_band`; does not fail the run but is surfaced for human review. See [D-30] and [D-32].
- **Eval staleness** — Eval coverage degrading as the corpus changes; addressed by re-seeding cases from updated taxonomy discovery samples. See [R-17].
- **Requirement group** — A set of extracted requirements that describe the same underlying behavior. Produced by two-stage grouping ([D-34]). One group → one `ConsolidatedRequirement`.
- **Conflict kind** — Explicit category of disagreement within a group: `contradiction`, `scope_mismatch`, `status_disagreement`, `version_skew`, or `type_disagreement`. See [D-35].
- **Reconciliation rules** — Ordered tie-breakers for resolving disagreement: manual override → source authority → recency → LLM judgment. See [D-10] and §3 Stage 4d.
- **Source authority** — Configured weight per source type (`config/consolidation.yaml: source_authority`) used in reconciliation and confidence scoring. Defaults are guesses; tunable via calibration. See [R-19].
- **Confidence signals** — The five observable inputs to the deterministic confidence formula: source count (log-scaled), authority-weighted agreement, recency spread penalty, statement similarity, conflict penalty. See [D-36].
- **Criticality level** — One of `critical | important | moderate | minor`, LLM-emitted with cluster summary as context. See [D-37].
- **Change plan flag** — Derived boolean on `ConsolidatedRequirement`: true if any contributing requirement was `type: change_plan` or `status: planned | proposed`. Used for review-queue tagging but does not auto-promote criticality.
- **Review priority** — Computed ordering signal for the review queue. Default formula: `criticality_numeric * (1 - confidence)`. Tunable in `config/consolidation.yaml`.
- **Calibration case** — A hand-authored record (`CalibrationCase`) pairing a frozen consolidated requirement with a target priority/criticality. Used to tune confidence weights and validate criticality assessment. See [D-39].
- **Calibration loop** — `calibrate:run` (executes cases against current weights, judges them) → review proposed weights → `calibrate:accept` (writes `config/calibration/tuned_weights.yaml`). Human-gated mirror of taxonomy lock. See [D-39].
- **Tuned weights** — Confidence weights produced by calibration tuning, overriding defaults from `config/consolidation.yaml` when accepted. Live in `config/calibration/tuned_weights.yaml`.
- **Cross-cluster reconciliation** — Stage 4.5: detects conflicts between consolidated requirements that live in different cluster subtrees and never share a per-cluster consolidation pass. See [D-40].
- **Cross-cluster candidate** — A pair of consolidated requirements from different clusters whose embedding similarity exceeds the cross-cluster threshold; produced by Stage 4.5a before LLM verification.
- **Cross-cluster verdict** — One of `confirmed_conflict | not_a_conflict | needs_review`. The third option exists deliberately so LLM uncertainty surfaces for human judgment rather than being forced into a binary.
- **Cross-cluster annotation** — A sidecar file (`cross_cluster_annotations.json`) per affected cluster, linking that cluster's `ConsolidatedRequirement` records to entries in the top-level `cross_cluster/conflicts.json`. Preserves immutability of Stage 4 outputs ([D-42]).
- **Cross-cluster boost** — Configurable additive contribution to `review_priority` for items participating in confirmed cross-cluster conflicts. Default 0.20. See [D-40].
- **Candidate cap** — Hard limit (`cross_cluster.max_candidate_pairs`, default 500) on cross-cluster candidate pairs; exceeding halts Stage 4.5 with a warning. See [D-44].
- **Report** — Stage 5.5 output: a timestamped markdown document the consultant reads first to decide where to focus. Deterministically rendered from existing pipeline artifacts; no LLM calls. See [D-45].
- **ReportRun** — The YAML frontmatter block written into each report capturing input versions, counts, and freshness warnings. Makes a report self-describing.
- **Freshness signal** — A computed indicator that some pipeline artifact may be out of date relative to current configuration: eval freshness (per LLM-driven step), calibration staleness (vs. consolidation config changes), taxonomy `--from-starting` shortcut, model pin drift. Surfaced in the report's Health section. See [D-47].
- **Report section** — One of the independently authored renderers in Stage 5.5 (`top_queue`, `landscape`, `health`, `provenance`). Configurable via `config/report.yaml: sections`. See [D-48].
- **Archived cluster** — A cluster with `archived: true` in `clusters/_index.yaml`. Excluded from active summarization, consolidation, cross-cluster reconciliation, and full report rendering. Files remain readable; member docs stay put. See [D-49] through [D-52].
- **`archived_at_versions`** — Snapshot of `consolidation`, `clustering`, and `taxonomy` config versions captured at archival time. Enables answering "what was the pipeline state when this cluster was archived?" without git archaeology. See [D-49].

---

## 8. Document conventions

- `[D-N]` Design decision, defined in §4.
- `[R-N]` Known risk, defined in §5.
- `[OPEN-N]` Open question / deep-dive area, defined in §6.
- Cross-references use these markers inline; the canonical entry lives in its section.
- Changes to data shapes (§2.3) are breaking changes and require a corresponding decision entry in §4.
- Resolved open questions are kept in §6 with a `RESOLVED` (or `PARTIALLY ADDRESSED`) marker and a pointer to where the resolution lives. They are not deleted, so the history of design moves stays readable.
