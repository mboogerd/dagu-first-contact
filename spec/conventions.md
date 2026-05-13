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

> The extractor reads the full normalized doc [NEEDS CLARIFICATION: does it also consult `evidence/` when normalization_kind is curated_summary? See D-23 but confirm for this extractor specifically].

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

## Risks and open questions

- A **risk** is a known failure mode we've accepted with mitigations. New risks are appended to `risks.md`.
- An **open question** is a deferred design or scope decision. New ones go into `open-questions.md` with: the question, why it matters, what would resolve it, and the trigger that should re-open it.
