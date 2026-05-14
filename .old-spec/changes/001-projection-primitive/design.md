# Design — [001] Projection primitive

## Approach

Introduce a **projection** as a named, resolvable, parameterized operation that takes an evidence record and produces one or more downstream-ready normalized documents. Replace the existing `normalization_kind: raw_text | curated_summary` enum with explicit projections per source. Move all "make evidence downstream-ready" logic into projection implementations.

### The mental model

```
evidence/<source>/<id>/            ← raw, immutable. May be a folder (e.g., git clone).
        │
        │  one or more named projections, resolved through the registry
        ▼
projections/<source>/<id>/<projection>/   ← projection's workspace and output(s)
        │   ├── *.md                       ← one or more normalized markdown docs
        │   ├── *.embedding.json           ← sidecar embeddings (per content_hash + prefix)
        │   └── <intermediates>            ← projection-specific working files
        │
        ▼   downstream stages read directly from here
extract / cluster / consolidate / ...
```

**The `projections/` tree IS the normalized layer.** There is no separate `normalized/` tree in this design. Every downstream stage reads from `projections/<source>/<id>/<projection>/<file>.md`. The "normalized doc shape" is the same uniform `{markdown + frontmatter}` as before; only the location changes.

### Why this works

- **Evidence stays bit-identical.** The current immutability invariant is preserved without contortion. A git clone in `evidence/git/<repo>/` is never mutated by the projection layer.
- **Multi-projection without folder reshuffling.** A single evidence record can have any number of projections, each in its own folder. The encapsulation the consultant asked for (multi-file projections kept together) falls out naturally.
- **Source-agnostic downstream.** Extractors and clustering read `projections/<source>/<id>/<projection>/*.md`. They don't care how the file got there. The git special case disappears.
- **Cache key falls out.** Projection caching is a function of (projection_name, projection_version, projection_params, evidence_content_hash, optionally model + prompt_version). Re-runs are free when inputs are unchanged.

## The projection contract

Every projection produces one or more **projection output files**, each a normalized markdown document. The contract a projection MUST honor:

1. **Frontmatter schema.** Every output file has the frontmatter described in [Frontmatter schema](#frontmatter-schema) below.
2. **Deterministic naming.** Output filenames within `projections/<source>/<id>/<projection>/` are deterministic functions of the projection's inputs and parameters. Re-running with the same inputs produces the same filenames.
3. **Per-projection body contract.** Each projection NAME has its own contract for the markdown body (e.g., `repo_summary` keeps its five fixed sections). Contracts live in the projection's specification document under `spec/projections/<projection-name>.md` (a new convention introduced by this change; see [Projection contract files](#projection-contract-files)).
4. **Idempotence.** Running the projection twice with identical inputs produces identical outputs. LLM-based projections achieve this via cache key + temperature=0; deterministic projections trivially.
5. **No mutation of evidence.** Projection implementations MUST NOT write into `evidence/`.

## Projection identifier and resolution

A projection name is a string of the form `<adapter>:<projection>`, where:

- `<adapter>` is the name of the source-type adapter (currently: `git`, `jira`, `rfp`, `spreadsheet`, `transcript`).
- `<projection>` is the projection name within that adapter.

Examples in v1:

- `git:repo_summary` — the LLM-curated summary, today's behavior.
- `jira:ticket_render` — deterministic rendering of a Jira ticket to markdown.
- `rfp:whole_document` — the whole RFP as one markdown doc (today's behavior).
- `rfp:section_split` — the same RFP split into one doc per section. **New in v1.**
- `spreadsheet:table_render` — deterministic flattening of a spreadsheet to markdown.
- `transcript:speaker_grouped` — deterministic rendering with speaker turn boundaries preserved.

### Projection registry

The registry maps projection names to concrete implementations. An implementation is one of:

- A **deterministic function** in code (e.g., the spreadsheet renderer).
- An **MCP tool** invocation (declared by tool name + transport).
- An **LLM skill** invocation (prompt template + structured-output schema + model).

[NEEDS CLARIFICATION (C-1): Physical form of the registry. Three candidates:

- **(a)** `config/projections.yaml` — a single file mapping names to implementation kinds and their config. Simple; matches the rest of the config layout.
- **(b)** `assessment/projections/<name>/` — one directory per projection containing implementation code, prompt templates, and schemas. More uniform with the per-adapter pattern; bigger up-front change.
- **(c)** A Python registry decorator in adapter modules. Most pythonic; least diffable.

Recommendation: **(a)** with a per-projection markdown contract file under `spec/projections/<name>.md`. Confirm before implementation.]

The registry entry for a projection minimally contains:

```yaml
git:repo_summary:
  kind: llm_skill
  prompt: prompts/repo_summary.md
  schema: schemas/repo_summary.schema.json
  model: <pinned id from config/models.yaml>
  default_intent: implemented
  parameters_schema: schemas/repo_summary.params.schema.json   # see C-2

jira:ticket_render:
  kind: deterministic
  module: assessment.projections.jira_ticket_render
  default_intent: implemented
  parameters_schema: null

rfp:whole_document:
  kind: deterministic
  module: assessment.projections.rfp_whole_document
  default_intent: proposed

rfp:section_split:
  kind: deterministic
  module: assessment.projections.rfp_section_split
  default_intent: proposed
```

### Parameter passing

A projection MAY accept parameters declared in `config/sources.yaml` per evidence record. Parameters are passed verbatim to the implementation. Their values are recorded in each output file's frontmatter under `projection_params`.

[NEEDS CLARIFICATION (C-2): Parameter schemas. Leaning toward requiring a JSON Schema per projection that has parameters (the `parameters_schema` field above). Validation happens at projection invocation; invalid parameters fail loudly. Confirm before implementation.]

### Projection contract files

Each projection has a contract file at `spec/projections/<adapter>__<projection>.md` (filesystem-safe form of `<adapter>:<projection>`) describing:

- **Purpose.** What this projection produces and for what consumer.
- **Inputs.** What evidence shape it expects.
- **Parameters.** Schema, defaults, semantics.
- **Output contract.** Filename pattern, frontmatter expectations specific to this projection, body contract (sections, ordering).
- **Cache key.** What invalidates a cached output.
- **Failure modes.**

Contract files live under `spec/projections/` (a new top-level directory). They are normal spec documents and follow the same review process as component specs.

In v1, this change ships contract files for all six listed projections (`git:repo_summary`, `jira:ticket_render`, `rfp:whole_document`, `rfp:section_split`, `spreadsheet:table_render`, `transcript:speaker_grouped`).

## Directory layout

Top-level changes:

```
assessment/
├── evidence/
│   └── <source>/<id>/...           ← unchanged
├── projections/                     ← NEW; replaces normalized/
│   └── <source>/<id>/
│       └── <projection>/
│           ├── <output-file>.md         ← projection output (one or many)
│           ├── <output-file>.embedding.<prefix>.json   ← embeddings; see embedding spec
│           └── <intermediates>          ← projection-specific working files (optional)
│
├── extracted/                       ← unchanged, but reads from projections/ now
├── clusters/                        ← unchanged
...
```

`normalized/` is removed. Existing references in code and spec are updated.

Note: when a projection produces a *single* output file, the file is named identically to the source_id (`projections/jira/PROJ-123/ticket_render/PROJ-123.md`). When multiple, names are projection-defined (e.g., `projections/rfp/doc-12/section_split/01-introduction.md`).

## Frontmatter schema

Updated schema for every projection output file:

```yaml
---
# Provenance (existing, lightly renamed)
source_type: jira                       # the adapter name; same values as before
source_id: PROJ-123                     # stable id of the underlying evidence
source_date: 2026-02-14                 # from evidence; ISO date if known
ingested_at: 2026-05-13T10:00:00Z
content_hash: <sha256 of this file's body>

# Projection (NEW)
projection: jira:ticket_render          # the projection that produced this file
projection_version: <semver or hash>    # version of the projection's contract+impl
projection_params: {}                   # passed through from config/sources.yaml
parent_evidence: jira/PROJ-123          # path under evidence/; the source artifact

# Intent (NEW)
intent: implemented                     # implemented | planned | proposed | mixed
default_status: implemented             # extractor's default status for requirements
                                        # from this projection, unless contrary evidence

# Origin record (kept for adapters that produced this file)
original_path: evidence/jira/PROJ-123.md

# Source-specific metadata (existing)
extra:
  jira_status: done
  jira_reporter: alice@example.com
---

<markdown body — per-projection contract>
```

**Changes from current schema:**

- Removed: `normalization_kind` (its purpose is subsumed by `projection`).
- Added: `projection`, `projection_version`, `projection_params`, `parent_evidence`, `intent`, `default_status`.
- The `content_hash` continues to be over the markdown body. Frontmatter is not part of `content_hash` (so that an `intent` correction doesn't invalidate embeddings).

## Intent declaration

`intent` and `default_status` are declared **per projection**, not per evidence record. The projection's contract picks the defaults; per-evidence overrides happen via `config/sources.yaml` when needed.

Semantics:

- `implemented` — projection produces docs describing built state. Default for git, jira (when ticket status is `done`), spreadsheet (when describing existing integrations).
- `planned` — projection produces docs describing committed-but-unbuilt state. Default for the (future) client estimation report adapter.
- `proposed` — projection produces docs describing discussed-but-uncommitted state. Default for RFP projections, transcripts.
- `mixed` — projection produces docs whose intent varies per record (e.g., a Jira project where some tickets are done and others are planned). The extractor MUST infer status per requirement; the projection's `default_status` is `unknown`.

[NEEDS CLARIFICATION (C-3): Whether `intent: mixed` is necessary in v1. The Jira case is the obvious one: a Jira project has tickets across all status values. Two options:

- **(a)** Jira tickets ship with `intent: mixed`, `default_status: unknown`, and the extractor uses each ticket's `jira_status` to set status per requirement.
- **(b)** Jira splits into projections by status: `jira:ticket_render_done`, `jira:ticket_render_planned`. Cleaner per-projection intent but multiplies projections and feels over-engineered for what is essentially "look at the ticket's status."

Recommendation: **(a)** — `intent: mixed` exists; the extractor handles per-ticket status as today. Confirm.]

### Effect on conflict detection

The `status_disagreement` conflict kind ([cross-reference: consolidate spec]) is suppressed when the difference between two sources' `status` is **explained by their projections' intents**. Specifically:

- A `Requirement` from a projection with `intent: planned` is allowed to have `status: planned` while another `Requirement` for the same group from a projection with `intent: implemented` has `status: implemented` — this is NOT a `status_disagreement` conflict; it is expected.
- A `Requirement` from a projection with `intent: mixed` is compared normally (its status was inferred per source, not declared by intent).

The rule is encoded in the consolidate stage's conflict detection phase as: "suppress `status_disagreement` when the set of source `intent` values is `{implemented, planned}` or `{implemented, proposed}` or `{planned, proposed}` and the resolved statuses align with those intents."

This is the primary defense against false conflicts when ingesting the client's estimation report alongside implemented code.

## Caching

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

Stored in the existing `cache/` directory.

Re-running a projection with no changes is free. Editing a projection's prompt or contract bumps `projection_version` (via the version hash in the contract file's frontmatter) and invalidates affected outputs.

### Cascading invalidation

When a projection output's `content_hash` changes:

- The embedding sidecar(s) for that file are invalidated (they already key on `content_hash`).
- Extraction caches that key on `doc_content_hash` are invalidated.
- Clustering re-runs in incremental mode pick up the changed doc on its next pass.

Layered caching downstream ([D-38](../../decisions/0038-layered-consolidation-caching.md)) already handles propagation correctly.

## Embedding implications

The [embedding spec](../../specs/embedding/spec.md) currently flags a `[NEEDS CLARIFICATION]` about how multiple prefixes per doc are stored. This change resolves it by placing sidecar embeddings inside each projection's folder:

```
projections/<source>/<id>/<projection>/
├── <output>.md
├── <output>.embedding.clustering.json   ← prefix encoded in filename
└── <output>.embedding.grouping.json
```

When no prefix conflict exists (most cases), filenames can omit the prefix suffix and default to `embedding.json` keyed to the `clustering: ` prefix. The full form is only used when multiple prefixes coexist.

The embedding spec delta (in this change's `specs/embedding/spec.md`) makes this concrete.

## Migration

When this change lands:

1. The implementer runs `python -m assessment ingest` once. The pre-existing `evidence/` is honored; all projections re-execute against it, populating `projections/<source>/<id>/<projection>/`. Cached LLM outputs from the previous `summarize_repo` calls survive (the cache key didn't change semantically — only the storage location did, and the cache key is over inputs, not output paths).
2. The old `normalized/` tree is deleted in the same commit that lands this change. It contains no information not reproducible from `evidence/` plus projections.
3. Downstream caches (extraction, clustering, consolidation) invalidate on changed `content_hash`. Most outputs will be bit-identical because most projections produce the same body as before (jira renders, RFP whole-document, spreadsheet flattening, transcript rendering). Git's `repo_summary` is the only one whose content_hash should be unchanged from before (the prompt and inputs didn't change). The only mass invalidation comes from frontmatter-only changes, which do NOT invalidate downstream caches because `content_hash` excludes frontmatter.

In practice: a single `ingest` + a single `cluster` + `consolidate` run after the migration produces an output equivalent to pre-migration plus the new `rfp:section_split` projections.

[NEEDS CLARIFICATION (C-4): Confirm the above migration plan. The "no downstream invalidation" outcome depends on `content_hash` excluding frontmatter. Confirm that holds.]

## Decisions promoted to top-level on landing

When this change lands, two new decision files are created in `spec/decisions/`:

- **`0053-projection-primitive.md`** — projection as a resolvable named operation; replaces `normalization_kind`. References this change folder.
- **`0054-source-declared-intent.md`** — intent declared per projection; suppresses false status_disagreement.

And one existing decision is superseded:

- **[D-22](../../decisions/0022-git-repo-curated-summary.md)** — superseded by D-53. Status becomes `Superseded by [D-53]`; content stays for historical record.

Decision numbers 53 and 54 are placeholders; landing picks the next free numbers at the time.
