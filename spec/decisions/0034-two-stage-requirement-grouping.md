# [D-34] Two-stage requirement grouping: embedding pre-grouping + LLM verification

**Status.** Accepted.

**Decision.** Consolidation groups requirements in two stages. First, embedding similarity above `grouping.embedding_threshold` produces candidate groups (deterministic, cheap, O(n²) similarity computation only within a cluster). Second, an LLM verification call per candidate group emits `confirm | split | reject`. Verification is cached on member content hashes + prompt version + model. An escape hatch (`grouping.llm_verification: false`) skips verification when cost-bounded.

**Rationale.** Pure embedding grouping misses paraphrased equivalents and over-groups near-but-different requirements. Pure LLM grouping is O(n²) per cluster and cost-prohibitive. The two-stage approach uses embeddings to collapse the search space and the LLM to catch the cases embeddings miss.

**Alternatives considered.**
- Pure embedding similarity — known failure modes on paraphrase and scope.
- Pure LLM grouping — cost-prohibitive at medium scale.
- Three-stage with a re-verification pass — marginal benefit.

**Trade-offs accepted.** Two failure surfaces (pre-grouping threshold + LLM verdict). Mitigation: pre-grouping threshold defaults are conservative (0.78); verification verdict and rationale are recorded in `groups.json` for inspection.

**Related.** [consolidate spec](../specs/consolidate/spec.md); [R-18](../risks.md).
