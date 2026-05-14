# Pending work

Captured at end of session 2026-05-13; consolidated 2026-05-14.

This file is a working backlog, not a spec artifact. It records what's known to be incomplete or pending across the spec, organized so each item can be picked up independently. Once an item is addressed, remove it (or move it to a change folder if it warrants one).

---

## Completed (2026-05-14)

The following high-priority structural work was completed in a single consolidation pass:

- **W-1** · Vault naming conventions — added to `spec/conventions.md`.
- **W-2** · Cluster → domain rename — completed throughout all specs, decisions, risks, open-questions.
- **W-3** · Cross-cluster → cross-domain restructure — dissolved into Stage 4 (phase 4f of consolidate). `specs/cross-cluster/` removed.
- **W-4** · Projection primitive — merged from change 001 into stable specs. Six projection contract files created under `spec/projections/`. New decisions D-49, D-50 created. D-22 superseded. Change 001 marked as Landed.
- **W-5** · Markdown-formatted artifacts with wikilinks — consolidated requirements are per-group markdown files; review queues are markdown tables with wikilinks.
- **W-6** · Open clarifications C-1..C-4 resolved: C-1 → directory per projection; C-2 → optional param schemas; C-3 → keep `intent: mixed`; C-4 → `content_hash` includes frontmatter.
- **W-9** · Glossary added (`spec/glossary.md`). Marker conventions paragraph added to `spec/conventions.md`.

---

## Lower-priority follow-ups (logged but not blocking)

### W-7 · Reviewer items revisited

Items deferred during the open-issues pass that still need resolution at some point:

- **Q-1** Adapter as directory key (vs. enum). Partly subsumed by the projection-registry pattern in D-49, but not fully resolved.
- **Q-4** Pure embedding-based domain assignment is not trustworthy enough — rework as candidate-reduction → LLM final assignment. Real design effort; deferred until first real run gives empirical signal.
- **Q-5** Taxonomy discovery should emit domain assignment hints. Couples with Q-4.
- **Q-6** Top-N priority should include subsystem centrality and resolution uncertainty. Cheap to implement; can land any time after consolidate is in code.
- **Q-7** Conflict feedback loop with the client (client answers as evidence; conflict lifecycle states; `conflict:resolve` operation). Comes after the basic pipeline is producing review queues.
- **Q-9b** Client estimation report ingestion. Unblocked by D-49/D-50 (projections + intent); needs a validation view downstream.
- **Q-10** Monolith handling via projections. Not relevant to current engagement.
- **Q-11** Transformation-estimate framing. Out of pipeline scope; deserves its own thin design doc later.
- **Q-12** Cross-domain scope (D-41: contradiction + scope_mismatch only) flagged for re-examination after first real run.

### W-8 · Other gaps surfaced during this session

- **Naming separator choice.** The chosen `__` separator may interact poorly with values that contain double underscores in identifiers. Confirm during implementation; switch separator if needed.
- **Embedding sidecar filename collision risk.** When a projection produces multiple outputs and each has a sidecar, ensure the naming convention prevents collisions. Spelled out in conventions; confirm coverage during implementation.
- **Domain-hierarchy is still flagged experimental.** A `[NEEDS CLARIFICATION]` exists in that spec about the proposal/apply workflow for super-domain mutations. Resolve before implementation.
- **Report Health section in v1 is small** (eval and calibration deferred). A `[NEEDS CLARIFICATION]` exists about whether to fold it into Provenance. Resolve when the report is implemented.
- **Initial-changes sketch in `spec/changes/README.md` is now stale** — the 9-change sequence was written before projection / domain / markdown decisions. Rewrite or delete and re-sketch.

---

## How to resume

1. **Read `spec/README.md`** to refresh the current shape.
2. **Pick the next item** from the lists above. All are independent and can be addressed in any order.
3. **Remove items from this file as they're addressed.** When this file is empty, delete it.
