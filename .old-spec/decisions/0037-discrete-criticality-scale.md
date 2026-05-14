# [D-37] Criticality is LLM-emitted on a fixed discrete scale, with cluster summary as context

**Status.** Accepted.

**Decision.** Criticality is one of four levels: `critical | important | moderate | minor`. The LLM emits the discrete level (not a float) via a single call with the resolved statement and the cluster's `summary.md` as context. The numeric value used for `review_priority` is looked up from `config/consolidation.yaml: criticality.numeric`. Cached on `hash(statement + cluster_summary_hash + prompt_version + model)`. The `change_plan_flag` is a separate, deterministic flag — it informs review-queue tags and an optional `change_plan_boost`, but does not override criticality.

**Rationale.** "Is this requirement central or peripheral to the cluster's scope?" is genuinely fuzzy; LLM judgment with cluster context is the right tool. But emitting floats is spurious precision. A four-level discrete scale is what an LLM can do reliably and what a reviewer can use.

**Alternatives considered.**
- Continuous 0..1 emitted by the LLM — spurious precision.
- Five levels — the additional level adds ambiguity, not signal.
- Heuristic criticality from source authority and reference count — a popularity proxy isn't importance.
- Constant criticality (drive priority from confidence only) — surfaces low-confidence trivia at the top.

**Trade-offs accepted.** Discrete levels can cluster at coarse granularity (many "important"). Calibration would catch this; v1 accepts the noise.

**Related.** [consolidate spec](../specs/consolidate/spec.md).
