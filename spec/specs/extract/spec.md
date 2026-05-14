# Extract (Stage 2)

Derive structured information of interest (requirements, interactions, concepts) from projection outputs.

**Phase.** Stage 2.

**Input → Output.** `projections/` + `config/taxonomy.locked.yaml` → `extracted/`.

**Prerequisite.** `config/taxonomy.locked.yaml` MUST exist. This stage refuses to run otherwise. The locked taxonomy supersedes the enum values defined below, which serve as the **starting taxonomy** (the floor).

---

## Approach

Three source-agnostic extractors run independently per projection output:

1. **`extract_requirements`** — produces `Requirement` rows. Captures `type` (functional / quality_attribute / constraint / assumption / change_plan) and `status` (implemented / planned / proposed / abandoned / unknown). Status MUST be set per source; the extractor uses the `adapter` field and source-specific cues as context to infer status (e.g., closed Jira ticket → likely `implemented` or `abandoned` depending on resolution; RFP statement → likely `proposed` or `planned`).

2. **`extract_interactions`** — produces `Interaction` rows for **runtime topology only**. Captures `kind`, `participants` (with explicit `bidirectional` flag when direction is unclear), `endpoint` (when available; degrades to service-level when not), and `evidence_strength` (observed / documented / inferred). Human collaboration, team ownership, and build-time-only dependencies are **out of scope** and MUST NOT be emitted.

3. **`extract_concepts`** — produces `Concept` rows of two kinds: `business_concept` and `technical_concept`. Both kinds may appear from the same source; the same concept may legitimately appear as both kinds with separate entries. Aliases are captured at extraction time to support consolidation merging.

Each extractor:

- Has its own prompt template in `config/prompts/` with a version hash recorded in the template's frontmatter (see [orchestration spec](../orchestration/spec.md) for how prompt versions feed cache keys).
- Reads the full projection output; `adapter` from the frontmatter is *context*, not *control flow*.
- Produces structured JSON via provider tool-calling, validated against the schemas below.
- Each projection output is treated as an independent input. A single piece of evidence with multiple projections produces multiple extraction runs (one per projection output).

### Raw evidence access

Extractors MAY consult the underlying `evidence/<adapter>/<source_id>/` when the projection's contract declares that evidence access is expected (e.g., `git:repo_summary` carries enough information that the extractor may want to dig into the underlying code). See [D-23].

### Status inference and intent

`extract_requirements` honors the `intent` and `default_status` frontmatter fields:

- When `intent` is `implemented | planned | proposed`, the extractor's default for each requirement's `status` is the projection's `default_status`.
- When `intent` is `mixed`, the extractor infers status per requirement as before (using adapter-specific cues and source-specific metadata in `extra:`).
- When the extractor has **strong contrary evidence**, it MAY override the default and emit a different status. The override is recorded with the requirement.

Every extraction call goes through the LLM cache. Cache key: `hash(prompt_text + doc_content_hash + model_id + schema + locked_taxonomy_version + projection_name + projection_version)`. A new taxonomy lock or projection version invalidates extraction cache automatically.

## Data shapes

### Requirement (`extracted/<adapter>/<source_id>/requirements.json`)

```json
{
  "id": "<source_id>:<local-index>",
  "statement": "The system must ...",
  "type": "functional | quality_attribute | constraint | assumption | change_plan",
  "status": "implemented | planned | proposed | abandoned | unknown",
  "source_id": "<projection output source_id>",
  "projection": "<projection that produced the input doc>",
  "source_excerpt": "<verbatim quote that justifies this requirement>",
  "source_date": "<from projection output>",
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

Status is set by the extractor per source. The same requirement appearing in code AND a Jira backlog ticket will produce two `Requirement` rows with different statuses; [consolidate](../consolidate/spec.md) reconciles them.

### Interaction (`extracted/<adapter>/<source_id>/interactions.json`)

An **interaction** is a runtime-topology relationship between two software components: one component depending on another for behavior or data at runtime. Out of scope: human collaboration, team ownership, build-time-only dependencies (use domain metadata for those).

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
  "source_id": "<projection output source_id>",
  "projection": "<projection that produced the input doc>",
  "source_date": "<from projection output>",
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
- `inferred` — not explicitly stated but strongly implied by context. Treat as hypothesis.

Downstream consumers MAY filter or weight by `evidence_strength`.

### Concept (`extracted/<adapter>/<source_id>/concepts.json`)

A **concept** is a named concept the system organizes itself around. Two kinds are tracked explicitly because they answer different questions.

```json
{
  "id": "<source_id>:<local-index>",
  "kind": "business_concept | technical_concept",
  "name": "Payments",
  "aliases": ["payment processing", "billing"],
  "description": "Concise statement of what this concept covers, in the source's own framing.",
  "evidence_excerpt": "<verbatim quote from source>",
  "source_id": "<projection output source_id>",
  "projection": "<projection that produced the input doc>",
  "source_date": "<from projection output>",
  "extracted_by": {
    "model": "<id>",
    "prompt_version": "<hash>"
  }
}
```

**`kind` semantics:**

- `business_concept` — a business capability or problem area (DDD-style). Examples: `Payments`, `Onboarding`, `Claims`, `Reporting`. Answers "what does the business do here?"
- `technical_concept` — an implementation-side area or concern. Examples: `Authentication`, `Event Bus`, `Data Warehouse`, `Frontend Shell`. Answers "what part of the technical stack is this?"

A single source can yield both kinds. The same concept may legitimately appear under both kinds (e.g., "Payments" as a business concept AND a technical subsystem); these are separate entries.

**`aliases` rationale.** Sources often use varying terminology for the same concept. Aliases are captured at extraction time and used during consolidation to merge entries.

## Directory layout

```
extracted/
└── <adapter>/<source_id>/
    ├── requirements.json
    ├── interactions.json
    └── concepts.json
```

## Related decisions

- [D-4](../../decisions/0004-source-agnostic-extractors.md) source-agnostic extractors.
- [D-5](../../decisions/0005-structured-outputs-only.md) structured outputs only.
- [D-16](../../decisions/0016-three-explicit-extractors.md) three extractors with distinct schemas.
- [D-23](../../decisions/0023-raw-evidence-accessible-to-extractors.md) raw evidence access.
- [D-49](../../decisions/0049-projection-primitive.md) projection primitive.
- [D-50](../../decisions/0050-source-declared-intent.md) source-declared intent.

## Failure modes

- Silent under-extraction (LLM returns three requirements where there are ten). Mitigation in v1: manual spot-checks during prompt development; defer the eval framework to a later phase.
- Inconsistency across re-runs when prompts change. Mitigation: prompt versioning is part of the cache key.
- Hallucinated `source_excerpt` / `evidence_excerpt` values not actually present in the doc. Mitigation: post-extraction validation that excerpts are substrings of the source.
- **Interaction over-extraction.** Extractor invents a direction from ambiguous evidence. Mitigation: schema requires `bidirectional: true` when direction can't be determined.
- **Interaction scope creep.** Extractor emits human-collaboration relationships ("Alice handed off to Bob"). Mitigation: prompt explicitly forbids.
- **Concept proliferation.** Every minor noun becomes a concept. Mitigation: prompt requires a minimum specificity threshold (a concept is something the source treats as a *named, scoped concept*, not any mentioned topic).
- **Status mis-classification.** Same code-implemented feature also has a stale "planned" Jira ticket; both extract correctly, consolidation must reconcile. Not a failure — by design.
- **Per-projection status mis-classification across same evidence.** A single piece of evidence with multiple projections may produce conflicting status values across projections of the same evidence. By design: each projection has its own intent; if two projections of the same evidence have different intents, the resulting requirements legitimately differ on status.
