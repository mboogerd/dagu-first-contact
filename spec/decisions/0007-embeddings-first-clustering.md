# [D-7] Embeddings-first clustering

**Status.** Accepted.

**Decision.** Structural clustering is embedding-based and deterministic. LLMs only label and summarize.

**Rationale.** LLM clustering of thousands of docs is non-deterministic, expensive, and hard to reproduce. Embeddings + fixed-seed clustering give the same tree on every run; LLMs handle the parts they're good at.

**Alternatives considered.**
- Pure LLM clustering — rejected: non-determinism.
- Pure embedding clustering with no labels — rejected: opaque.

**Trade-offs accepted.** Embedding-based assignment makes some semantic mistakes (see cluster-structural failure modes and [R-3](../risks.md)).

**Related.** [cluster-structural spec](../specs/cluster-structural/spec.md); [open-questions.md](../open-questions.md) (the consultant has flagged that pure embedding-based clustering may not be trustworthy enough — a future change folder may revise this).
