# [D-36] Confidence is a deterministic function of observable signals

**Status.** Accepted.

**Decision.** `Confidence.score` is computed by a deterministic weighted formula over five signals (source count, authority-weighted agreement, recency spread, statement similarity, conflict presence). The LLM is **not** consulted for the score itself. The LLM IS consulted for the human-readable parts: `Conflict.description` and `Conflict.resolution.rationale`. Both signals and weights are recorded in the `Confidence` object for auditability.

**Rationale.** Confidence needs to be explainable to the client and tunable. A hybrid deterministic-plus-LLM-adjustment design combines the worst of both: less reproducible than pure deterministic, less nuanced than pure LLM, and twice as hard to calibrate. Keeping the score deterministic and letting the LLM contribute to free-text fields preserves both auditability and prose quality.

**Alternatives considered.**
- Hybrid: deterministic base + per-item LLM adjustment — explainability suffers.
- Pure LLM-emitted confidence — non-deterministic.
- Drop confidence as a score — loses the review-queue ordering signal.

**Trade-offs accepted.** The deterministic formula will not capture every nuance. Default weights are guesses (calibration is deferred in v1; see [open-questions.md](../open-questions.md)). Mitigation: the five signals cover the dimensions that matter; edge cases that need finer reasoning surface through `Conflict.description`.

**Related.** [consolidate spec](../specs/consolidate/spec.md); [R-5](../risks.md), [R-6](../risks.md).
