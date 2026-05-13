# [001] Projection primitive

**Status.** Proposed
**Opened.** 2026-05-13
**Landed.** —

## Motivation

The current spec has one special-cased path: the git adapter produces an LLM-curated `RepoSummary` instead of a raw rendering of evidence. This works for git but doesn't generalize. Three concrete needs push us toward a real primitive:

1. **Cross-functional documents** (RFPs, spreadsheets) typically touch multiple subsystems. Normalizing them as a single document is wrong for clustering — the whole document gets assigned to a single cluster, washing out subsystem-specific signal. They should split into partials, one per subsystem they address.
2. **Large evidence with multiple useful angles.** A repo benefits from multiple projections (architecture summary, public-API surface, domain glossary) consumed by different stages. Future engagements with monoliths will need module-level projections of the same repo.
3. **The client's pre-existing estimation report** (incoming) describes *planned* work. We want to ingest it alongside implemented code without producing false `status_disagreement` conflicts. The cleanest way to express "this evidence describes intended state, not built state" is as a property of the projection that produced the normalized doc.

A general **projection primitive** addresses all three uniformly, and replaces the git special case with one instance of the general mechanism.

Out-of-band benefit: the resolution mechanism for projection names (deterministic function, MCP tool, or LLM skill) gives us a clean extension point for future evidence-shaping work without adding more special cases.

## Scope

### In scope

- The projection primitive: a named, resolvable, parameterized operation on an evidence record producing one or more downstream-ready normalized documents.
- A projection registry: how names resolve to concrete implementations (deterministic function, MCP tool, LLM skill).
- A new top-level `projections/` tree for projection outputs and intermediates. **The `projections/` tree IS the normalized layer; `normalized/` is removed.**
- Frontmatter schema additions: `projection`, `projection_version`, `projection_params`, `parent_evidence`, `intent` (and optional `default_status`).
- Retrofit of existing adapters: git, jira, rfp, spreadsheet, transcript. Each declares its v1 projection(s) explicitly.
- A single follow-up projection on RFP (`section_split`) as proof of multi-projection support. This is the smallest change that exercises the "one evidence → multiple normalized docs" path.
- Spec deltas for every component that reads or writes normalized docs: ingest, embedding, extract, cluster-structural, taxonomy.
- Source-declared intent (`intent: implemented | planned | proposed | mixed`) on projections, suppressing false `status_disagreement` conflicts when sources differ on status because their intents differ.

### Out of scope

- Monolith / module projections (Q-10) — needs a real monolith corpus to design against.
- Client estimation report adapter and validation view (Q-9b) — enabled by this change but deserves its own change folder.
- The conflict feedback loop (Q-7).
- Clustering rework (Q-4) — also enabled by this change but separate concern.
- Eval and calibration framework reintroduction (Q-9a, Q-8) — still deferred.
- Cluster archival (deferred).

## Success criteria

- `evidence/` content is bit-identical to before this change (immutability of raw evidence is preserved).
- `projections/<source>/<id>/<projection>/` exists for every previously-normalized doc, containing at least one markdown file plus an `embedding.json` sidecar.
- The git adapter no longer has special-case code paths in extract or cluster; its `repo_summary` projection is one entry in the projection registry alongside `jira:ticket_render`, `rfp:whole_document`, etc.
- A new `rfp:section_split` projection produces multiple normalized docs from one RFP, each landing in (potentially) different clusters at the next `cluster` run.
- Ingesting a document with `intent: planned` does NOT produce `status_disagreement` conflicts against implemented evidence for the same requirement.
- The change folder has no unresolved `[NEEDS CLARIFICATION]` markers at landing.

## Compliance with principles

- **Principle 1 (Filesystem-as-DB):** projections land as files; no new stores.
- **Principle 2 (Immutable layers):** `evidence/` stays untouched. Projections are a layer downstream of evidence; nothing inside projections is allowed to write back into evidence.
- **Principle 3 (Content-addressed caching):** projection cache key is `hash(projection_name + projection_version + projection_params + evidence_content_hash + (model + prompt_version if applicable))`.
- **Principle 4 (Uniform doc shape):** every projection output is still `{markdown + YAML frontmatter}`. The frontmatter schema grows but stays uniform.
- **Principle 5 (Deterministic orchestration):** projection resolution happens inside the ingest stage; orchestration code doesn't know about projection kinds.
- **Principle 6 (Structured outputs):** LLM-based projections continue to use provider tool-calling against per-projection schemas.
- **Principle 7 (Provenance preserved):** each projection output records `parent_evidence`, `projection`, `projection_version`, `projection_params`, and (where applicable) `model` + `prompt_version`.
- **Principle 8 (Cheap-first):** deterministic projections preferred where they suffice (jira tickets, RFP whole-document, spreadsheets, transcripts). LLM projections reserved for cases where curation is genuinely needed (repo_summary).

## Open clarifications

The change is not implementable until this section is empty. As of opening, these are unresolved:

- **C-1:** The projection registry's *physical form* — is it a `config/projections.yaml` file, a directory of registration modules, or something else? See [design.md §Projection registry](design.md#projection-registry).
- **C-2:** Parameter typing — projection parameters are YAML-serializable per the consultant's framing, but should there be a per-projection schema for parameter validation? Leaning yes for safety, but want to confirm before implementing.
- **C-3:** Whether `intent: mixed` is genuinely necessary in v1, or whether mixed-intent evidence should be required to declare a more specific projection (e.g., a Jira project where some tickets are planned and others done — does the *ticket* declare intent, or the *projection*?). See [design.md §Intent declaration](design.md#intent-declaration).
- **C-4:** Migration of existing `normalized/` content during the change implementation — full re-projection from `evidence/`, or in-place rewrite of frontmatter? Likely full re-projection (cheap and clean) but want to confirm before the implementer assumes.

## Related

- Open questions: Q-1, Q-2, Q-3, Q-9b, Q-10 in [../../open-questions.md](../../open-questions.md). This change resolves Q-2 and Q-3, lays groundwork for Q-9b and Q-10, and partially addresses Q-1 (the projection registry pattern is a precedent for an adapter registry).
- Decisions superseded: [D-22](../../decisions/0022-git-repo-curated-summary.md) becomes "the git adapter declares a `repo_summary` projection; the curation behavior moves to that projection's contract." The decision file stays; its status updates to `Superseded by [D-NN]` at landing.
- Decisions added (anticipated, finalized in design.md): a new decision for "projection as a resolvable named operation" and a new decision for "source-declared intent."
