# [D-26] Single global similarity threshold, manually tuned

**Status.** Accepted.

**Decision.** One `assignment_threshold` (default cosine 0.60) in `config/clustering.yaml` governs nearest-seed assignment for all source types. A `low_confidence_band` (default [0.55, 0.65]) flags borderline assignments for human review without rejecting them.

**Rationale.** Simplicity. Per-source thresholds add knobs without clear tuning signal at medium scale. The low-confidence band catches the cases where the threshold is wrong without forcing a re-run.

**Alternatives considered.**
- Per-source-type thresholds — too many knobs without enough data to tune them.
- Adaptive threshold per domain density — theoretically appealing but fiddly.
- Top-k assignment (always assign to nearest seed, no threshold) — forces misfit assignments.

**Trade-offs accepted.** A single threshold won't be optimal for every source type. Acceptable: the low-confidence band is the safety net.

**Related.** [domain-structural spec](../specs/domain-structural/spec.md).
