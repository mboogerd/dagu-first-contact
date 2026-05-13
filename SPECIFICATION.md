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

The pipeline has five layers plus a discovery artifact. Each layer is a directory; each is produced by one stage; none is mutated by downstream stages.

| # | Layer        | Directory       | Produced by stage  | Contents                                                  |
|---|--------------|-----------------|--------------------|-----------------------------------------------------------|
| 1 | Evidence     | `evidence/`     | Ingest             | Raw artifacts pulled from source, organized by source type |
| 2 | Normalized   | `normalized/`   | Ingest             | Uniform `{markdown + frontmatter}` view of every artifact  |
| — | Taxonomy     | `taxonomy/`     | Taxonomy Discovery | Discovery iterations + the locked taxonomy that Extract consumes |
| 3 | Extracted    | `extracted/`    | Extract            | Structured JSON extractions per document                   |
| 4 | Clusters     | `clusters/`     | Cluster            | Emergent organization; summaries; membership               |
| 5 | Consolidated | inside clusters | Consolidate        | Conflict-resolved requirements and review queue            |

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
│   ├── evals/                    # eval sets, one directory per LLM-driven step
│   │   ├── summarize_repo/
│   │   │   ├── cases/<case_id>.yaml
│   │   │   └── runs/<run_id>.json
│   │   ├── discover_taxonomy/
│   │   ├── extract_requirements/
│   │   ├── extract_interactions/
│   │   └── extract_domains/
│   └── prompts/                  # versioned prompt templates
│       ├── summarize_repo.md
│       ├── discover_taxonomy.md
│       ├── extract_requirements.md
│       ├── extract_interactions.md
│       ├── extract_domains.md
│       ├── label_cluster.md
│       ├── consolidate.md
│       └── judges/               # judge prompts (one per extractor that uses LLM-as-judge)
│           ├── judge_summarize_repo.md
│           └── judge_extract_requirements.md
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
  member_count: 47
  summary_hash: <hash of summary inputs>   # cache key
  seeded_from: git:payments-service        # provenance of cluster creation
  origin: seed | orphan                    # seed = git-derived; orphan = HDBSCAN-discovered
```

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
- For each cluster, generate `summary.md` covering responsibilities and interactions, from member docs and their extractions.
- Orphan clusters additionally get a meaningful name (replacing `orphan-<index>`) generated from their summary; the rename is recorded in `_index.yaml`.
- Cache key: `hash(sorted(member_content_hashes) + prompt_version + model)`.
- Summary only regenerates when membership or member content changes.

**3c · Hierarchy (LLM, low frequency).**
- `identifySuperClusters`: given sibling cluster summaries within a path, propose groupings.
- Output is a proposed tree edit applied to `_index.yaml`.
- Re-summarization of new parents cascades but is cached, so unchanged subtrees cost nothing.

**3d · Archival.**
- Manual flag in `_index.yaml`. Archived clusters are skipped in all subsequent summarization and consolidation.
- Archived git repos do **not** seed clusters in phase 3a re-runs.

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
python -m assessment consolidate        # bottom-up
python -m assessment report             # generates the human-facing summary
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

### [OPEN-3] Cross-cluster conflict reconciliation
**Why it matters.** The most interesting conflicts are often between subsystems (Jira says X for cluster A, RFP says Y for cluster B, code does Z somewhere else). Bottom-up consolidation underweights these.
**What would resolve it.** Choice between:
1. A final global pass over all consolidated requirements (expensive; loses cluster context).
2. Cross-cluster "conflict candidate" detection via embedding similarity across cluster boundaries, with targeted LLM verification.
3. Accept the limitation; document that distant-branch conflicts are out of scope for the automated pipeline and surface only what root-cluster consolidation finds.

Default recommendation: option 2.

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

---

## 8. Document conventions

- `[D-N]` Design decision, defined in §4.
- `[R-N]` Known risk, defined in §5.
- `[OPEN-N]` Open question / deep-dive area, defined in §6.
- Cross-references use these markers inline; the canonical entry lives in its section.
- Changes to data shapes (§2.3) are breaking changes and require a corresponding decision entry in §4.
- Resolved open questions are kept in §6 with a `RESOLVED` (or `PARTIALLY ADDRESSED`) marker and a pointer to where the resolution lives. They are not deleted, so the history of design moves stays readable.
