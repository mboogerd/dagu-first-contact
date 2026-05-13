# [D-45] Report is a deterministic rendering of existing artifacts; no LLM calls

**Status.** Accepted.

**Decision.** The report stage makes zero LLM calls. The report is purely a rendering of artifacts produced by upstream stages. All content — top-N items, landscape, freshness warnings, provenance, handover — is computed from existing files using deterministic logic.

**Rationale.** The report's job is to *present* what the pipeline already produced, not to generate new analysis. Every interesting judgment (criticality, conflict rationale, cluster summaries) already has an LLM call and provenance elsewhere; replicating that work at report time would duplicate cost and introduce non-determinism.

**Alternatives considered.**
- LLM-generated executive summary at report time — duplicates work; non-deterministic.
- Re-run criticality/confidence at report time — those belong to consolidation; re-running them mid-report would mean the report disagrees with `review_queue.json`.
- A "narrative" section that uses an LLM to synthesize themes — nice-to-have; can be added later. Out of scope for v1 (see [R-25](../risks.md)).

**Trade-offs accepted.** The report won't have the polished narrative an LLM could synthesize. Acceptable: the audience is the consultant, who is in the best position to synthesize.

**Related.** [report spec](../specs/report/spec.md).
