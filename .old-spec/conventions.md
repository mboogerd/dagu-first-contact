# Spec conventions

How to author and evolve this spec, with the small set of discipline tactics borrowed from `spec-kit` and the change-folder structure borrowed from `OpenSpec`.

---

## File roles

| File / directory | Stability | Role |
|---|---|---|
| `principles.md` | Highly stable | Immutable constraints. The "constitution." |
| `specs/<component>/spec.md` | Stable | Externally-observable behavior contract per component. |
| `decisions/<NNNN>-slug.md` | Append-only | One decision per file (ADR-style). Past decisions stay; superseded ones are marked, not deleted. |
| `risks.md` | Stable, edits ok | Accepted risks with mitigations. |
| `open-questions.md` | Stable, edits ok | Deferred items, with the trigger that would re-open them. |
| `changes/<NNN>-slug/` | Per-iteration | The unit of new work. See [changes/README.md](changes/README.md). |

## The change folder is the ticket

New work happens in `changes/<NNN>-slug/`. Each change folder contains:

- `proposal.md` — what & why, in/out scope, success criteria.
- `design.md` — decisions specific to this change, with rationale.
- `tasks.md` — numbered, parallelizable checklist.
- `specs/<component>/spec.md` — **delta** against the stable component spec (ADDED / MODIFIED / REMOVED sections). Merges into the stable spec when the change lands.

A change folder is the unit an LLM agent can be asked to implement. Specs themselves don't get edited mid-change; the deltas land at merge time.

See [changes/README.md](changes/README.md) for the template.

## `[NEEDS CLARIFICATION: ...]` markers

When generating any spec content (proposal, design, delta), the author (human or LLM) **must** flag ambiguities with `[NEEDS CLARIFICATION: <question>]` rather than silently guessing.

Examples:

> The extractor reads the full projection output [NEEDS CLARIFICATION: does it also consult `evidence/` when the projection contract declares evidence access? See D-23 but confirm for this extractor specifically].

> Threshold defaults to 0.78 [NEEDS CLARIFICATION: validated against actual corpus, or carried over from v0 guess?].

Before a change folder is implementable, all clarifications in it must be resolved. Reviewers should fail a change that contains unresolved markers.

## `[P]` parallel task markers

In `tasks.md`, a task that can be executed in parallel with adjacent tasks is marked `[P]`:

```
1. Define adapter registry interface
2. [P] Implement git adapter
2. [P] Implement jira adapter
2. [P] Implement rfp adapter
3. Wire adapters into ingest CLI
```

Tasks with the same number and `[P]` are siblings that can run in any order or concurrently. Tasks at different numbers are sequential.

## How content moves between layers

```
new idea
   │
   ▼
changes/<NNN>-slug/proposal.md  ── may add [NEEDS CLARIFICATION] markers
   │
   ▼
changes/<NNN>-slug/design.md    ── may propose new decisions
   │
   ▼
changes/<NNN>-slug/tasks.md     ── [P] markers where applicable
   │
   ▼
implementation (out of scope of this spec)
   │
   ▼
on landing:
   ── proposal/design/tasks archived under changes/<NNN>-slug/
   ── delta in changes/<NNN>-slug/specs/ merges into stable specs/<component>/spec.md
   ── any new decisions become decisions/<NNNN>-slug.md (next free number)
   ── any new risks become risks.md entries
```

The change folder is never deleted; it's the audit trail.

## Decision documents

One file per decision. Format:

```markdown
# [D-NN] <Decision title>

**Status.** Accepted | Superseded by [D-MM] | Deprecated

**Decision.** One paragraph.

**Rationale.** Why this and not the alternatives.

**Alternatives considered.** Bulleted list.

**Trade-offs accepted.** What we knowingly give up.

**Related.** Other decisions, specs, risks this connects to.
```

Decision numbers (`[D-N]`) match the filename prefix and are not reused. When a decision is superseded, the file stays; its status becomes `Superseded by [D-MM]` and the superseding decision references it back.

## Component spec documents

`specs/<component>/spec.md` describes **externally-observable behavior**: inputs, outputs, contracts with adjacent components, and the data shapes that cross component boundaries. Implementation details (algorithms, internal data structures) belong in design documents (either inside a change folder or, for long-lived design notes, alongside the spec).

Each component spec should include:

- A phase tag in the heading where one applies (e.g., `# Ingest (Stage 1)`).
- Input/output summary.
- Behavior in normal cases.
- Failure modes and how the component handles them.
- Cross-references to related decisions and risks.

If a component's behavior changes meaningfully, the change must:

1. Open a change folder.
2. Capture the delta in `changes/<NNN>-slug/specs/<component>/spec.md`.
3. Resolve any `[NEEDS CLARIFICATION]` markers before implementation.
4. Merge the delta into the stable component spec on landing.

## Cross-reference markers

The spec uses a small set of inline markers for cross-referencing:

- **`[D-N]`** — reference to design decision N. The N matches the filename prefix in `decisions/`. Example: `[D-14]` refers to `decisions/0014-deterministic-orchestration.md`.
- **`[R-N]`** — reference to risk N. The N matches the entry heading in `risks.md`.
- **`[NEEDS CLARIFICATION: ...]`** — flags a silent assumption that must be resolved before the surrounding content is implementable. Reviewers should fail a change that contains unresolved markers.
- **`[P]`** — in `tasks.md`, marks a task that can run in parallel with adjacent same-numbered tasks.

## Risks and open questions

- A **risk** is a known failure mode we've accepted with mitigations. New risks are appended to `risks.md`.
- An **open question** is a deferred design or scope decision. New ones go into `open-questions.md` with: the question, why it matters, what would resolve it, and the trigger that should re-open it.

---

## Vault and runtime artifact naming conventions

The assessment root is one Obsidian vault. The conventions below apply to **runtime pipeline artifacts** (the files the pipeline produces), not to spec files.

### Top-level directory structure

```
evidence/           ← raw, immutable evidence per source
projections/        ← projection outputs (the normalized layer)
extracted/          ← structured extractions per projection output
domains/            ← domain tree (renamed from clusters/)
taxonomy/           ← discovery iterations, findings, proposal
reports/            ← timestamped report snapshots
cache/              ← LLM call cache
config/             ← all configuration files
```

### Adapter as directory key

The adapter name (e.g., `git`, `jira`, `rfp`) is the top-level folder under `evidence/`, `projections/`, and `extracted/`. It is NOT a hardcoded enum — it's the adapter's registered name, which is also its directory name. See [D-51](decisions/0051-adapter-registry.md).

- `evidence/<adapter>/`
- `projections/<adapter>/<source-id>/`
- `extracted/<adapter>/<source-id>/`

Examples: `evidence/jira/`, `projections/jira/PROJ-123/`, `extracted/git/payments-service/`.

### Projection output folders

A projection MAY create subfolders for its outputs. When it does, the subfolder is named `<projection>/` under the source-id folder:

```
projections/<adapter>/<source-id>/<projection>/
├── <output>.md
├── <output>.embedding.json
└── <intermediates>
```

### Filename convention

Filenames within scope folders follow the pattern:

```
<adapter>__<source-id>__<projection>[__<output-id>].<role>.<ext>
```

The `__` (double underscore) separator is chosen so Obsidian wikilinks can use the filename directly without path disambiguation.

- `<role>` indicates the file's purpose: e.g., `summary`, `requirements`, `review-queue`.
- `<ext>` is the file extension: `.md`, `.json`, `.yaml`.
- `<output-id>` is present only for multi-output projections.

### Domain (cluster) hierarchy as folders

Domains preserve hierarchy as folders. Per-domain files within each folder are prefixed with the domain name so wikilinks resolve without needing the full path:

```
domains/
├── _index.yaml
├── _assignments.json
├── root__review-queue.md
├── root__cross-domain-findings.md
├── financial-domain/
│   ├── financial-domain__summary.md
│   ├── financial-domain__review-queue.md
│   └── payments-service/
│       ├── payments-service__summary.md
│       ├── payments-service__review-queue.md
│       └── payments-service__groups/
│           ├── payments-service__group-0001.md
│           └── payments-service__group-0002.md
```

### Embedding sidecars

Embedding sidecars live next to their projection output with `.embedding.json` suffix (or `.embedding.<prefix>.json` for multi-prefix cases):

```
projections/jira/PROJ-123/ticket_render/PROJ-123.embedding.json
projections/jira/PROJ-123/ticket_render/PROJ-123.embedding.grouping.json
```

When only one prefix is in use (the common case), the prefix suffix is omitted and the file defaults to the `clustering: ` prefix.

### Cross-references in frontmatter

Frontmatter cross-references between artifacts SHOULD be wikilink-shaped string values so Obsidian backlinks resolve:

```yaml
parent_evidence: "[[jira__PROJ-123]]"
domain: "[[payments-service__summary]]"
```

### Separator choice

The `__` separator may interact poorly with values that naturally contain double underscores. If this is encountered in practice, the separator can be changed in a future revision. For v1, no known source identifiers contain `__`.
