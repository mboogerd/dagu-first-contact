# Ingest (Stage 1)

Pull raw evidence from sources; run projections to produce downstream-ready documents.

**Phase.** Stage 1.

**Input → Output.** `config/sources.yaml` → `evidence/` + `projections/`.

---

## Behavior

### Adapter responsibilities

Each source-type adapter has a single responsibility: fetch raw evidence into `evidence/<source_type>/...` (idempotent — skip if unchanged).

Adapters in scope for v1: `git`, `jira`, `spreadsheet`, `rfp`, `transcript`. Adding a new source type means writing one adapter; nothing downstream changes.

### Projection execution

For each evidence record, the ingest CLI runs **every projection registered for that record's source type** (as declared in `config/sources.yaml`), producing one or more files in `projections/<source>/<id>/<projection>/`.

Projection execution is shared infrastructure, not the adapter's job. The git adapter is not special: its `summarize_repo` LLM call is the implementation of the `git:repo_summary` projection; the adapter itself does only fetching of `evidence/git/<repo>/`.

### Projection contract

Every projection produces one or more **projection output files**, each a normalized markdown document. The contract a projection MUST honor:

1. **Frontmatter schema.** Every output file has the frontmatter described in [Frontmatter schema](#frontmatter-schema) below.
2. **Deterministic naming.** Output filenames within `projections/<source>/<id>/<projection>/` are deterministic functions of the projection's inputs and parameters. Re-running with the same inputs produces the same filenames.
3. **Per-projection body contract.** Each projection has its own contract for the markdown body, specified in the projection's contract file under `spec/projections/<adapter>__<projection>.md`.
4. **Idempotence.** Running the projection twice with identical inputs produces identical outputs. LLM-based projections achieve this via cache key + temperature=0; deterministic projections trivially.
5. **No mutation of evidence.** Projection implementations MUST NOT write into `evidence/`.

### Projection identifier and resolution

A projection name is a string of the form `<adapter>:<projection>`. Examples in v1:

- `git:repo_summary` — LLM-curated summary of a git repo.
- `jira:bulk_download` — deterministic rendering of Jira tickets to markdown (one file per ticket).
- `rfp:whole_document` — the whole RFP as one markdown doc.
- `rfp:section_split` — the same RFP split into one doc per section.
- `spreadsheet:table_render` — deterministic flattening of a spreadsheet to markdown.
- `transcript:speaker_grouped` — deterministic rendering with speaker turn boundaries preserved.

### Projection registry

The registry maps projection names to concrete implementations. Each projection has a directory under `assessment/projections/<adapter>__<projection>/` containing its implementation code, prompt templates (if LLM-based), and schemas. An implementation is one of:

- A **deterministic function** in code (e.g., the spreadsheet renderer).
- An **MCP tool** invocation (declared by tool name + transport).
- An **LLM skill** invocation (prompt template + structured-output schema + model).

### Projection parameters

A projection MAY accept parameters declared in `config/sources.yaml` per evidence record. Parameters are passed verbatim to the implementation. Their values are recorded in each output file's frontmatter under `projection_params`.

Projections that take parameters SHOULD declare a JSON Schema for parameter validation. Validation happens at projection invocation; invalid parameters fail loudly. Projections with no parameters have `parameters_schema: null`.

## Data shapes

### Frontmatter schema (projection output)

Every projection output file has this frontmatter:

```yaml
---
# Provenance
source_type: jira
source_id: PROJ-123
source_date: 2026-02-14
ingested_at: 2026-05-13T10:00:00Z
content_hash: <sha256 of entire file including frontmatter>

# Projection
projection: jira:bulk_download
projection_version: <hash of (prompt + schema + model id) for LLM-skill; hash of source for deterministic; pinned version for MCP>
projection_params: {}
parent_evidence: "[[evidence/jira/PROJ-123]]"

# Intent
intent: implemented          # implemented | planned | proposed | mixed
default_status: implemented  # extractor's default status for requirements from this projection

# Source-specific metadata
extra:
  jira_status: done
  jira_reporter: alice@example.com
---

<markdown body — per-projection contract>
```

**`content_hash`** is computed over the entire file (frontmatter + body). A change to any field (including `intent` corrections) invalidates downstream caches. This is intentional: the trade-off of re-computation on frontmatter edits is accepted in favor of simpler, more predictable cache invalidation.

**`intent`** and **`default_status`** are declared per projection, not per evidence record. The projection's contract picks the defaults; per-evidence overrides happen via `config/sources.yaml` when needed.

Intent semantics:

- `implemented` — docs describing built state. Default for `git:repo_summary`, `jira:bulk_download` (when ticket status is `done`).
- `planned` — docs describing committed-but-unbuilt state.
- `proposed` — docs describing discussed-but-uncommitted state. Default for RFP projections, transcripts.
- `mixed` — docs whose intent varies per record. The extractor MUST infer status per requirement; the projection's `default_status` is `unknown`. Used by `jira:bulk_download` because a Jira project has tickets across all status values; the extractor reads each ticket's `extra.jira_status` to set status per requirement.

### Source configuration (`config/sources.yaml`)

```yaml
sources:
  git:
    - id: payments-service
      url: git@github.com:client/payments-service.git
      projections:
        - name: git:repo_summary
          parameters: {}
  jira:
    - id: PROJ
      api_endpoint: ...
      projections:
        - name: jira:bulk_download
          parameters: {}
  rfp:
    - id: doc-12
      source_path: evidence_inputs/doc-12.pdf
      projections:
        - name: rfp:whole_document
          parameters: {}
        - name: rfp:section_split
          parameters:
            min_section_length: 200
```

Sources MAY declare multiple projections. The pipeline produces one or more outputs per projection.

### Projection cache key

```
hash(
  projection_name,
  projection_version,
  serialized(projection_params),
  evidence_content_hash,
  (model, prompt_version)  if kind == llm_skill
)
```

Re-running a projection with no changes is free. Editing a projection's prompt or contract bumps `projection_version` and invalidates affected outputs.

### Cascading invalidation

When a projection output's `content_hash` changes:

- The embedding sidecar(s) for that file are invalidated (they key on `content_hash`).
- Extraction caches that key on `doc_content_hash` are invalidated.
- Domain assignment re-runs in incremental mode pick up the changed doc on its next pass.

## Directory layout (relative to the assessment root)

```
evidence/
└── <source_type>/<source_id>/...     ← raw, immutable

projections/
└── <source_type>/<source_id>/
    └── <projection>/
        ├── <output>.md               ← projection output(s)
        ├── <output>.embedding*.json  ← embedding sidecars (see embedding spec)
        └── <intermediates>           ← optional, projection-specific
```

(Embedding sidecars live alongside the projection output; see [embedding](../embedding/spec.md).)

## Related decisions

- [D-1](../../decisions/0001-filesystem-as-db.md) filesystem-as-DB.
- [D-2](../../decisions/0002-uniform-normalized-doc-shape.md) uniform doc shape.
- [D-3](../../decisions/0003-adapter-pattern-for-ingestion.md) adapter pattern.
- [D-49](../../decisions/0049-projection-primitive.md) projection primitive.
- [D-50](../../decisions/0050-source-declared-intent.md) source-declared intent.

## Failure modes

- Lossy normalization (e.g., spreadsheets with rich formatting flattened too aggressively).
- Stale `evidence/` if upstream changed but our cache says "fetched recently."
- Spreadsheets and RFPs that defy markdown conversion (large tables, embedded images).
- Jira tickets with thousands of comments blowing past context windows in later stages.
- **Projection registry mismatch.** A `config/sources.yaml` declares a projection name not in the registry. Ingest fails fast with a clear error.
- **Per-projection failures stay isolated.** If `rfp:section_split` fails for one document, `rfp:whole_document` for the same document still completes. Failures are recorded per (evidence, projection) pair.
