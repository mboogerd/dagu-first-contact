# [D-47] Freshness signals are first-class report content

**Status.** Accepted (scope reduced in v1).

**Decision.** The Health section of every report computes and surfaces concrete freshness signals. Warnings appear both in the frontmatter (`freshness_warnings`) and in human-readable form in the Health section.

**v1 signals:**

- **Taxonomy freshness:** if `taxonomy.locked.yaml` was locked via the `--from-starting` shortcut, emit `taxonomy_from_starting` warning.
- **Model pin drift:** detect when any model id in `models.yaml` has a newer pinnable version available (best-effort; provider-dependent; non-blocking).

**Deferred to a later phase** (when the corresponding features return):

- Eval freshness per LLM-driven step. Deferred with the eval framework.
- Calibration staleness vs. consolidation config changes. Deferred with calibration.

**Rationale.** Voluntary disciplines need surfacing. The report is the natural place because it's what the consultant actually reads. Making warnings unmissable (frontmatter + body) closes the gap between "the spec says do this" and "the spec helps you notice when you didn't."

**Alternatives considered.**
- Health as a separate command (`status` or `doctor`) — easy to skip.
- Freshness as warnings in stage output only — scrolls past.
- No freshness signals — too much hard-won discipline elsewhere to abandon here.

**Trade-offs accepted.** Freshness checks add computation at report time and may produce false positives. Acceptable: computation is local (no LLM calls); false positives are informative not blocking.

**Related.** [report spec](../specs/report/spec.md).
