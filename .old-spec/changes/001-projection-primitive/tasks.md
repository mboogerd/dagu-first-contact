# Tasks — [001] Projection primitive

Tasks at the same number with `[P]` markers can run in parallel.

## Pre-flight

- [ ] 1. Resolve all `[NEEDS CLARIFICATION]` markers in `proposal.md` and `design.md` (C-1, C-2, C-3, C-4). No code is written before this is done.

## Specification work (no code)

- [ ] 2. Write the projection contract files under `spec/projections/`:
  - [ ] 2. [P] `spec/projections/git__repo_summary.md`
  - [ ] 2. [P] `spec/projections/jira__ticket_render.md`
  - [ ] 2. [P] `spec/projections/rfp__whole_document.md`
  - [ ] 2. [P] `spec/projections/rfp__section_split.md`
  - [ ] 2. [P] `spec/projections/spreadsheet__table_render.md`
  - [ ] 2. [P] `spec/projections/transcript__speaker_grouped.md`

- [ ] 3. Merge the spec deltas in this change folder's `specs/` into their respective stable component specs:
  - [ ] 3. [P] `specs/ingest/spec.md` ← `changes/001-projection-primitive/specs/ingest/spec.md`
  - [ ] 3. [P] `specs/extract/spec.md` ← `changes/001-projection-primitive/specs/extract/spec.md`
  - [ ] 3. [P] `specs/embedding/spec.md` ← `changes/001-projection-primitive/specs/embedding/spec.md`
  - [ ] 3. [P] `specs/cluster-structural/spec.md` ← `changes/001-projection-primitive/specs/cluster-structural/spec.md`
  - [ ] 3. [P] `specs/taxonomy/spec.md` ← `changes/001-projection-primitive/specs/taxonomy/spec.md`

- [ ] 4. Promote new decisions to top-level decision files:
  - [ ] 4. [P] `spec/decisions/00XX-projection-primitive.md` (next free number)
  - [ ] 4. [P] `spec/decisions/00YY-source-declared-intent.md` (next free number)

- [ ] 5. Update `spec/decisions/0022-git-repo-curated-summary.md` status to `Superseded by [D-XX]` (the new projection-primitive decision).

- [ ] 6. Update `spec/decisions/README.md` index with the two new decisions and the superseded D-22.

- [ ] 7. Remove the resolved `[NEEDS CLARIFICATION]` in `specs/embedding/spec.md` (about multiple-prefix sidecars). It's resolved by this change.

- [ ] 8. Update `spec/README.md` if any top-level layout descriptions reference `normalized/`.

- [ ] 9. Update `spec/open-questions.md`:
  - Q-2 (projection primitive) → mark resolved; point to this change.
  - Q-3 (source-declared intent) → mark resolved; point to this change.
  - Q-9b (client estimation report) → note that the prerequisite (Q-2, Q-3) is now resolved; the validation view is the open follow-up.

## Implementation

[NEEDS CLARIFICATION: The change folder does not own implementation details. The tasks below are the *shape* of the implementation work, intentionally light. The implementer writes the actual code-shaped tasks when starting the implementation phase.]

- [ ] 10. Implement the projection registry per design.md C-1's resolution.
- [ ] 11. Implement deterministic projections:
  - [ ] 11. [P] `jira:ticket_render`
  - [ ] 11. [P] `rfp:whole_document`
  - [ ] 11. [P] `rfp:section_split`
  - [ ] 11. [P] `spreadsheet:table_render`
  - [ ] 11. [P] `transcript:speaker_grouped`
- [ ] 12. Migrate the existing `summarize_repo` LLM call into the `git:repo_summary` projection.
- [ ] 13. Update the ingest CLI to drive projections from `config/sources.yaml`.
- [ ] 14. Update extract, embedding, cluster-structural, taxonomy to read from `projections/` instead of `normalized/`.
- [ ] 15. Update the consolidate stage's `status_disagreement` detection to honor `intent` (per design.md §Effect on conflict detection).
- [ ] 16. Delete `normalized/` from the working copy of the assessment workspace. Update gitignore if applicable.

## Tests / validation

- [ ] T1. Round-trip: ingest → projection → extract on a sample evidence set produces bit-identical extract outputs to a pre-migration run for the same inputs.
- [ ] T2. `rfp:section_split` produces ≥2 normalized docs from a representative multi-section RFP, each with distinct `content_hash`.
- [ ] T3. Two sources with different intents (one `intent: planned`, one `intent: implemented`) describing the same requirement DO NOT produce a `status_disagreement` conflict.
- [ ] T4. Editing a projection's prompt/contract bumps `projection_version` and invalidates the cache for affected outputs only; outputs of unrelated projections are unaffected.
- [ ] T5. The `evidence/` tree is byte-identical before and after running `ingest`.
- [ ] T6. Frontmatter changes (e.g., correcting an `intent`) do NOT change `content_hash` and therefore do NOT invalidate downstream caches.

## Landing checklist

- [ ] L1. All clarifications above resolved.
- [ ] L2. All tests pass.
- [ ] L3. Spec deltas merged into stable component specs.
- [ ] L4. New decisions promoted; D-22 marked superseded.
- [ ] L5. Open questions updated.
- [ ] L6. This change folder's `proposal.md` status updated to `Landed` with date.
