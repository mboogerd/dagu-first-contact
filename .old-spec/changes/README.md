# Changes

This is where new work lives. Each change is a folder, and each folder is the unit an LLM agent can be asked to implement.

## Folder structure

```
changes/<NNN>-<slug>/
├── proposal.md   # what & why, scope (in/out), success criteria
├── design.md     # decisions specific to this change, with rationale
├── tasks.md      # numbered, parallelizable checklist
└── specs/        # delta against the stable specs (optional; only when behavior changes)
    └── <component>/
        └── spec.md   # uses ADDED / MODIFIED / REMOVED sections
```

`<NNN>` is a zero-padded sequential number (`001`, `002`, ...). `<slug>` is a short kebab-case description.

## Workflow

1. **Open.** Create a new folder. Number is the next free integer. Start with `proposal.md`.
2. **Draft.** Fill in `proposal.md`, `design.md`, `tasks.md`. Use `[NEEDS CLARIFICATION: ...]` markers liberally; resolve them before implementation.
3. **Implement.** Execute `tasks.md`. Update task checkboxes as you go. Implementation is out of scope of this spec but happens against the artifacts here.
4. **Land.** When implementation is done:
   - Merge any `specs/` deltas into the stable component specs under `../specs/<component>/spec.md`.
   - Promote any new decisions into `../decisions/<NNNN>-slug.md` (next free number).
   - Append any new risks to `../risks.md`.
   - Mark the change as landed in its `proposal.md` (status line at top).
5. **Keep.** The change folder is never deleted. It's the audit trail of why the spec looks the way it does.

## Template — proposal.md

```markdown
# [NNN] <Change title>

**Status.** Proposed | In progress | Landed | Abandoned
**Opened.** YYYY-MM-DD
**Landed.** YYYY-MM-DD (or blank)

## Motivation

Why this change. One or two paragraphs. What problem it solves, what becomes possible.

## Scope

### In scope

- Bullet list.

### Out of scope

- Bullet list. Things adjacent to this change that intentionally don't get done here.

## Success criteria

Concrete, checkable outcomes. Not "improves X" but "after this change, `cluster --full` completes in under 30 seconds on the 35-repo corpus."

## Open clarifications

List any `[NEEDS CLARIFICATION: ...]` markers that are still unresolved. The change is not implementable until this section is empty.
```

## Template — design.md

```markdown
# Design — [NNN] <Change title>

## Approach

How the change is implemented at a level above code. Algorithms, data flow, key data structures.

## Decisions

Per-decision blocks. One per non-obvious choice made within this change.

### Decision: <short title>

- **Choice.** What we chose.
- **Rationale.** Why.
- **Alternatives considered.** What we rejected, briefly.
- **Trade-offs.** What we accept.

(When a decision is broad enough to outlive this change, promote it to a top-level decision document at landing time.)

## Compliance with principles

Show how this change respects each principle that's relevant. Flag any deviation explicitly with rationale; deviations require human review.

## Data shape impact

If the change touches any data shape that crosses component boundaries, describe the change here. The actual delta lives in `specs/<component>/spec.md`.

## Caching impact

If the change invalidates any cache, describe what gets invalidated and why. Cache invalidation is correctness-critical.
```

## Template — tasks.md

```markdown
# Tasks — [NNN] <Change title>

Numbered. Tasks at the same number with `[P]` markers can run in parallel.

- [ ] 1. <First task>
- [ ] 2. [P] <Task A>
- [ ] 2. [P] <Task B>
- [ ] 3. <Task that depends on 2.A and 2.B both>
- [ ] 4. <...>

## Tests

- [ ] T1. <Test or validation that proves the change works>
```

## Template — specs/<component>/spec.md (delta)

Only present when this change modifies behavior of an existing component (or introduces a new one).

```markdown
# Delta — <component>

## ADDED

- New behavior the component will have after this change.

## MODIFIED

- Existing behavior that changes. Quote the old behavior and the new.

## REMOVED

- Behavior the component will no longer have.
```

When the change lands, this delta is merged into the stable `../specs/<component>/spec.md` and the delta file stays in the change folder as historical record.

## Initial planned changes

A sketch of the first few implementation changes (subject to refinement):

1. `001-projection-primitive` — **Landed.** Projection primitive, source-declared intent, six projection contracts.
2. `002-evidence-and-adapters` — adapter registry, the first two adapters (git, jira), evidence fetch + projection execution.
3. `003-taxonomy-discovery` — Stage 1.5 (simplified: no eval).
4. `004-extraction` — three extractors (`extract_requirements`, `extract_interactions`, `extract_concepts`) with prompt versioning.
5. `005-domain-assignment-v0` — embedding-based assignment + repo seeds + HDBSCAN; no hierarchy yet.
6. `006-domain-hierarchy` — Stage 3c super-domains (kept per consultant request; experimental).
7. `007-consolidation-v0` — bottom-up with cross-domain findings, deterministic confidence with default weights, LLM criticality, markdown group files, review queue markdown tables.
8. `008-report-v0` — review queue rendering + landscape + provenance sections + handover artifact.

The first runnable end-to-end version is after `008`. The order is a suggestion; it may shift as we learn.
